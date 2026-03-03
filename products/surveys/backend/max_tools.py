"""
MaxTool for AI-powered survey creation and analysis.
"""

from datetime import timedelta
from textwrap import dedent
from typing import Any

import django.utils.timezone

from asgiref.sync import sync_to_async
from pydantic import BaseModel, ConfigDict, Field

from posthog.schema import (
    SurveyAnalysisQuestionGroup,
    SurveyAnalysisResponseItem,
    SurveyAppearanceSchema,
    SurveyCreationSchema,
    SurveyDisplayConditionsSchema,
    SurveyQuestionSchema,
    SurveyType,
)

from posthog.constants import DEFAULT_SURVEY_APPEARANCE
from posthog.exceptions_capture import capture_exception
from posthog.models import Survey, Team

from products.surveys.backend.summarization.fetch import fetch_responses

from ee.hogai.tool import MaxTool


def get_team_survey_config(team: Team) -> dict[str, Any]:
    """Get team survey configuration for context."""
    survey_config = getattr(team, "survey_config", {}) or {}
    return {
        "appearance": survey_config.get("appearance", {}),
        "default_settings": {"type": "popover", "enable_partial_responses": True},
    }


SURVEY_CREATION_TOOL_DESCRIPTION = dedent("""
    Use this tool to create and optionally launch in-app surveys based on structured survey configurations.

    # When to use
    - The user wants to create a new survey
    - The user wants to launch a survey for collecting feedback
    - The user mentions NPS, CSAT, PMF, or feedback surveys

    # Critical Survey Design Principles
    **These are in-app surveys that appear as overlays while users are actively using the product.**
    - **Keep surveys SHORT**: 1-3 questions maximum - users are trying to accomplish tasks
    - **Focus on ONE key insight**: Don't try to gather everything at once
    - **Prioritize user experience**: A short survey with high completion is better than a long abandoned one

    # Survey Types
    - **popover** (default): Small overlay that appears on the page - most common for in-app surveys
    - **widget**: Widget that appears via CSS selector or embedded button
    - **api**: Headless survey for custom implementations

    # Question Types
    1. **open**: Free-form text input (feedback, suggestions)
    2. **single_choice**: Select one option (Yes/No, satisfaction levels)
    3. **multiple_choice**: Select multiple options (feature preferences)
    4. **rating**: Numeric (1-10 for NPS, 1-5 for CSAT) or emoji scale
    5. **link**: Display a link with call-to-action

    # Common Survey Patterns
    - **NPS**: "How likely are you to recommend us?" (rating scale 10, number display)
    - **CSAT**: "How satisfied are you with X?" (rating scale 5)
    - **PMF**: "How would you feel if you could no longer use X?" (single_choice with specific options)
    - **Feedback**: Open-ended questions about experience

    # Feature Flag Targeting
    When targeting by feature flag:
    - User must provide the flag ID (integer) from a prior search
    - Set `linked_flag_id` to the integer flag ID
    - For variant targeting, add `linkedFlagVariant` in conditions
    """).strip()


class CreateSurveyToolArgs(BaseModel):
    survey: SurveyCreationSchema = Field(
        description=dedent("""
        The complete survey configuration to create.

        # Required Fields
        - **name**: Survey name (e.g., "NPS Survey", "Onboarding Feedback")
        - **description**: Brief survey description
        - **type**: "popover" (default), "widget", or "api"
        - **questions**: Array of question objects (see Question Structure below)

        # Optional Fields
        - **should_launch**: Set to true to launch immediately, false for draft (default: false)
        - **linked_flag_id**: Integer feature flag ID for targeting users with a specific flag
        - **conditions**: Display conditions object (URL targeting, wait period, etc.)
        - **appearance**: Custom appearance settings (colors, positioning)
        - **start_date**: ISO date string to schedule launch
        - **end_date**: ISO date string to end survey
        - **responses_limit**: Maximum number of responses to collect

        # Question Structure
        Each question requires:
        - **type**: "open", "rating", "single_choice", "multiple_choice", or "link"
        - **question**: The question text to display

        Optional per question:
        - **id**: Unique identifier (auto-generated if not provided)
        - **description**: Additional context below the question
        - **optional**: Whether the question can be skipped (default: false)
        - **buttonText**: Text for the continue button

        For **rating** questions:
        - **scale**: Number of points (5, 7, or 10). Use 10 for NPS, 5 for CSAT
        - **display**: "number" or "emoji"
        - **lowerBoundLabel**: Label for low end (e.g., "Not likely")
        - **upperBoundLabel**: Label for high end (e.g., "Very likely")

        For **single_choice**/**multiple_choice** questions:
        - **choices**: Array of option strings

        For **link** questions:
        - **link**: URL to link to
        - **buttonText**: Link button text

        # Conditions Structure
        - **url**: URL path string to match (e.g., "/pricing", "/dashboard")
        - **urlMatchType**: How to match URL - "exact", "icontains" (contains, case-insensitive), "not_icontains", "regex", "not_regex", "is_not"
        - **seenSurveyWaitPeriodInDays**: Number of days to wait after user has seen any survey before showing this one
        - **deviceTypes**: Array of device types to target, e.g., ["Mobile"], ["Desktop", "Tablet"]
        - **deviceTypesMatchType**: Match type for devices - same options as urlMatchType
        - **linkedFlagVariant**: Feature flag variant to target (requires linked_flag_id)
        - **selector**: CSS selector for element-based targeting (e.g., "#signup-button")

        # Examples

        ## NPS Survey
        ```json
        {
            "name": "NPS Survey",
            "description": "Net Promoter Score survey",
            "type": "popover",
            "questions": [{
                "type": "rating",
                "question": "How likely are you to recommend us to a friend or colleague?",
                "scale": 10,
                "display": "number",
                "lowerBoundLabel": "Not likely at all",
                "upperBoundLabel": "Extremely likely"
            }],
            "should_launch": false
        }
        ```

        ## NPS with Follow-up
        ```json
        {
            "name": "NPS with Feedback",
            "description": "NPS with optional follow-up question",
            "type": "popover",
            "questions": [
                {
                    "type": "rating",
                    "question": "How likely are you to recommend us?",
                    "scale": 10,
                    "display": "number",
                    "lowerBoundLabel": "Not likely",
                    "upperBoundLabel": "Very likely"
                },
                {
                    "type": "open",
                    "question": "What could we improve?",
                    "optional": true
                }
            ],
            "should_launch": false
        }
        ```

        ## Targeted Survey (URL + Feature Flag)
        ```json
        {
            "name": "Pricing Page Feedback",
            "description": "Feedback from pricing page visitors",
            "type": "popover",
            "linked_flag_id": 123,
            "conditions": {
                "url": "/pricing",
                "urlMatchType": "icontains"
            },
            "questions": [{
                "type": "single_choice",
                "question": "Is our pricing clear?",
                "choices": ["Yes, very clear", "Somewhat clear", "Not clear at all"]
            }],
            "should_launch": true
        }
        ```

        # Critical Rules
        - Keep to 1-3 questions maximum
        - DO NOT set should_launch=true unless the user explicitly requests to launch
        - NPS uses scale=10, CSAT uses scale=5
        - First question should typically be required (optional: false), follow-ups can be optional
        """).strip()
    )


class CreateSurveyTool(MaxTool):
    name: str = "create_survey"
    description: str = SURVEY_CREATION_TOOL_DESCRIPTION
    args_schema: type[BaseModel] = CreateSurveyToolArgs

    def get_required_resource_access(self):
        return [("survey", "editor")]

    async def is_dangerous_operation(self, survey: SurveyCreationSchema, **kwargs) -> bool:
        """Launching a survey immediately is a dangerous operation."""
        return survey.should_launch is True

    async def format_dangerous_operation_preview(self, survey: SurveyCreationSchema, **kwargs) -> str:
        """Format a human-readable preview of the dangerous operation."""
        survey_name = survey.name or "Untitled Survey"
        question_count = len(survey.questions) if survey.questions else 0
        return f"**Create and launch** survey '{survey_name}' with {question_count} question(s). It will immediately start collecting responses."

    async def _arun_impl(self, survey: SurveyCreationSchema) -> tuple[str, dict[str, Any]]:
        """
        Create a survey from the structured configuration.
        """
        try:
            user = self._user
            team = self._team

            if not survey.questions:
                return "Survey must have at least one question", {
                    "error": "validation_failed",
                    "error_message": "No questions provided in the survey configuration.",
                }

            # Apply appearance defaults and prepare survey data
            survey_data = self._prepare_survey_data(survey, team)

            # Set launch date if requested
            if survey.should_launch:
                survey_data["start_date"] = django.utils.timezone.now()

            # Link to insight if provided in context (e.g., from funnel cross-sell)
            if self.context.get("insight_id"):
                survey_data["linked_insight_id"] = self.context["insight_id"]

            # Create the survey directly using Django ORM
            created_survey = await Survey.objects.acreate(team=team, created_by=user, **survey_data)

            launch_msg = " and launched" if survey.should_launch else ""
            return f"Survey '{created_survey.name}' created{launch_msg} successfully!", {
                "survey_id": created_survey.id,
                "survey_name": created_survey.name,
            }

        except Exception as e:
            capture_exception(e, {"team_id": self._team.id, "user_id": self._user.id})
            return f"Failed to create survey: {str(e)}", {"error": "creation_failed", "details": str(e)}

    def _prepare_survey_data(self, survey_schema: SurveyCreationSchema, team: Team) -> dict[str, Any]:
        """Prepare survey data with appearance defaults applied."""
        # Convert schema to dict, removing should_launch field
        if hasattr(survey_schema, "model_dump"):
            survey_data = survey_schema.model_dump(exclude_unset=True, exclude={"should_launch"})
        else:
            survey_data = survey_schema.__dict__.copy()
            survey_data.pop("should_launch", None)

        # Ensure required fields have defaults
        survey_data.setdefault("archived", False)
        survey_data.setdefault("description", "")
        survey_data.setdefault("enable_partial_responses", True)

        # Apply appearance defaults
        appearance = DEFAULT_SURVEY_APPEARANCE.copy()

        # Override with team-specific defaults if they exist
        team_appearance = get_team_survey_config(team).get("appearance", {})
        if team_appearance:
            appearance.update(team_appearance)

        # Finally, override with survey-specified appearance settings
        if survey_data.get("appearance"):
            survey_appearance = survey_data["appearance"]
            # Convert to dict if needed
            if hasattr(survey_appearance, "model_dump"):
                survey_appearance = survey_appearance.model_dump(exclude_unset=True)
            elif hasattr(survey_appearance, "__dict__"):
                survey_appearance = survey_appearance.__dict__
            # Only update fields that are actually set (not None)
            appearance.update({k: v for k, v in survey_appearance.items() if v is not None})

        # Always set appearance to ensure surveys have consistent defaults
        survey_data["appearance"] = appearance

        return survey_data


SURVEY_EDIT_TOOL_DESCRIPTION = dedent("""
    Use this tool to edit an existing survey.

    # When to use
    - User wants to modify a survey's name, description, or questions
    - User wants to launch or stop a survey
    - User wants to archive a survey
    - User wants to change survey targeting conditions

    # Finding the Survey
    First use the search tool with kind="surveys" to find the survey ID, then use this tool.

    # Common Operations
    - **Launch**: Set start_date to "now"
    - **Stop**: Set end_date to "now"
    - **Archive**: Set archived to true
    - **Update questions**: Provide full questions array (replaces existing)
    - **Update conditions**: Provide conditions object (replaces existing)

    # Important Notes
    - Only include fields you want to change in the updates
    - When updating questions, you must provide the complete list (it replaces existing)
    - You cannot edit a survey that doesn't belong to your team
    """).strip()


class SurveyUpdateSchema(BaseModel):
    """Partial schema for survey updates - only include fields to change."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    type: SurveyType | None = None
    questions: list[SurveyQuestionSchema] | None = None
    conditions: SurveyDisplayConditionsSchema | None = None
    appearance: SurveyAppearanceSchema | None = None
    linked_flag_id: int | None = None
    start_date: str | None = Field(default=None, description='ISO date string or "now" to launch immediately')
    end_date: str | None = Field(default=None, description='ISO date string or "now" to stop immediately')
    archived: bool | None = None
    responses_limit: int | None = None
    enable_partial_responses: bool | None = None


class EditSurveyToolArgs(BaseModel):
    survey_id: str = Field(description="UUID of the survey to edit")
    updates: SurveyUpdateSchema = Field(description="Fields to update on the survey")


class EditSurveyTool(MaxTool):
    name: str = "edit_survey"
    description: str = SURVEY_EDIT_TOOL_DESCRIPTION
    args_schema: type[BaseModel] = EditSurveyToolArgs

    def get_required_resource_access(self):
        return [("survey", "editor")]

    async def is_dangerous_operation(self, survey_id: str, updates: SurveyUpdateSchema, **kwargs) -> bool:
        """Launching, stopping, or archiving a survey are dangerous operations."""
        return updates.start_date == "now" or updates.end_date == "now" or updates.archived is True

    async def format_dangerous_operation_preview(self, survey_id: str, updates: SurveyUpdateSchema, **kwargs) -> str:
        """Format a human-readable preview of the dangerous operation."""
        # Try to get survey name for a better preview
        survey_name = survey_id
        try:
            survey = await sync_to_async(Survey.objects.get)(id=survey_id, team=self._team)
            survey_name = f"'{survey.name}'"
        except Survey.DoesNotExist:
            survey_name = f"(ID: {survey_id})"

        actions = []
        if updates.start_date == "now":
            actions.append("**Launch** the survey (it will start collecting responses)")
        if updates.end_date == "now":
            actions.append("**Stop** the survey (it will stop collecting responses)")
        if updates.archived is True:
            actions.append("**Archive** the survey")

        if len(actions) == 1:
            return f"{actions[0]} {survey_name}"
        else:
            action_list = "\n".join(f"- {action}" for action in actions)
            return f"Perform the following actions on survey {survey_name}:\n{action_list}"

    async def _arun_impl(self, survey_id: str, updates: SurveyUpdateSchema) -> tuple[str, dict[str, Any]]:
        """
        Edit an existing survey with the provided updates.
        """
        try:
            team = self._team

            # Fetch the existing survey
            try:
                survey = await sync_to_async(Survey.objects.get)(id=survey_id, team=team)
            except Survey.DoesNotExist:
                return f"Survey with ID '{survey_id}' not found", {
                    "error": "not_found",
                    "error_message": f"No survey found with ID '{survey_id}' in your team.",
                }

            # Get the updates as a dict, excluding None values
            update_data = updates.model_dump(exclude_unset=True)

            if not update_data:
                return "No updates provided", {
                    "error": "no_updates",
                    "error_message": "No fields were provided to update.",
                }

            # Handle special date values
            if update_data.get("start_date") == "now":
                update_data["start_date"] = django.utils.timezone.now()
            if update_data.get("end_date") == "now":
                update_data["end_date"] = django.utils.timezone.now()

            # Handle nested objects that need conversion
            if "questions" in update_data and update_data["questions"] is not None:
                update_data["questions"] = [
                    q.model_dump(exclude_unset=True) if hasattr(q, "model_dump") else q
                    for q in update_data["questions"]
                ]

            if "conditions" in update_data and update_data["conditions"] is not None:
                conditions = update_data["conditions"]
                update_data["conditions"] = (
                    conditions.model_dump(exclude_unset=True) if hasattr(conditions, "model_dump") else conditions
                )

            if "appearance" in update_data and update_data["appearance"] is not None:
                appearance = update_data["appearance"]
                # Merge with existing appearance
                existing_appearance = survey.appearance or {}
                new_appearance = (
                    appearance.model_dump(exclude_unset=True) if hasattr(appearance, "model_dump") else appearance
                )
                update_data["appearance"] = {**existing_appearance, **new_appearance}

            # Apply updates to survey
            for field, value in update_data.items():
                setattr(survey, field, value)

            await sync_to_async(survey.save)()

            # Build response message
            updated_fields = list(update_data.keys())
            actions = []
            if "start_date" in updated_fields and updates.start_date == "now":
                actions.append("launched")
            if "end_date" in updated_fields and updates.end_date == "now":
                actions.append("stopped")
            if "archived" in updated_fields and updates.archived:
                actions.append("archived")

            if actions:
                action_str = " and ".join(actions)
                message = f"Survey '{survey.name}' has been {action_str} successfully!"
            else:
                fields_str = ", ".join(updated_fields)
                message = f"Survey '{survey.name}' updated successfully! Modified fields: {fields_str}"

            return message, {
                "survey_id": str(survey.id),
                "survey_name": survey.name,
                "updated_fields": updated_fields,
            }

        except Exception as e:
            capture_exception(e, {"team_id": self._team.id, "user_id": self._user.id})
            return f"Failed to edit survey: {str(e)}", {"error": "edit_failed", "details": str(e)}


class SurveyAnalysisArgs(BaseModel):
    """Retrieve survey responses for analysis."""

    survey_id: str | None = Field(
        default=None,
        description="UUID of the survey to analyze. If not provided, uses survey from current context.",
    )


class SurveyAnalysisTool(MaxTool):
    name: str = "analyze_survey_responses"
    description: str = dedent("""
        Retrieve survey responses for analysis.

        # When to use
        - User asks to analyze survey responses or feedback
        - User wants to find themes, patterns, or insights from survey data
        - User asks about sentiment or recommendations from survey feedback

        # Finding the Survey
        If you don't have a survey_id, first use the search tool with kind="surveys" to find it.

        # What this tool returns
        Returns the raw open-ended responses from the survey which you should then analyze
        to extract themes, sentiment, and actionable insights.
    """).strip()
    args_schema: type[BaseModel] = SurveyAnalysisArgs

    def get_required_resource_access(self):
        return [("survey", "viewer")]

    def _format_responses_for_analysis(self, question_groups: list[SurveyAnalysisQuestionGroup]) -> str:
        """
        Format the grouped responses into a string for analysis.
        """
        formatted_sections = []

        for group in question_groups:
            question_name = group.questionName
            responses = group.responses

            formatted_sections.append(f'Question: "{question_name}"')

            response_texts = []
            if responses:
                for response in responses:
                    response_text = response.responseText
                    response_texts.append(f'- "{response_text}"')

            if response_texts:
                formatted_sections.append("Responses:\n" + "\n".join(response_texts))
            else:
                formatted_sections.append("Responses: (none)")
            formatted_sections.append("")

        return "\n".join(formatted_sections)

    async def _fetch_survey_responses(self, survey: Survey) -> list[SurveyAnalysisQuestionGroup]:
        """Fetch open-ended responses for a survey from the database."""
        questions = survey.questions or []
        question_groups: list[SurveyAnalysisQuestionGroup] = []

        # Use survey start_date or created_at as the start, and now as the end
        start_date = survey.start_date or survey.created_at or (django.utils.timezone.now() - timedelta(days=365))
        end_date = survey.end_date or django.utils.timezone.now()

        for idx, question in enumerate(questions):
            q_type = question.get("type", "")
            # Only fetch open-ended questions
            if q_type != "open":
                continue

            question_id = question.get("id")
            question_text = question.get("question", f"Question {idx + 1}")

            # Fetch responses for this question
            responses_list = await sync_to_async(fetch_responses)(
                survey_id=str(survey.id),
                question_index=idx,
                question_id=question_id,
                start_date=start_date,
                end_date=end_date,
                team=self._team,
                limit=50,  # Limit responses per question
            )

            # Convert to SurveyAnalysisResponseItem objects
            response_items = [
                SurveyAnalysisResponseItem(
                    responseText=text,
                    isOpenEnded=True,
                )
                for text in responses_list
                if text and text.strip()
            ]

            if response_items:
                question_groups.append(
                    SurveyAnalysisQuestionGroup(
                        questionName=question_text,
                        questionId=question_id or str(idx),
                        responses=response_items,
                    )
                )

        return question_groups

    async def _arun_impl(self, survey_id: str | None = None) -> tuple[str, dict[str, Any]]:
        """
        Retrieve survey responses for the main agent to analyze.
        Returns the formatted responses so the agent can extract themes, sentiment, and insights.
        """
        try:
            # Try to get survey_id from argument first, then from context
            context = self.context or {}
            effective_survey_id = survey_id or context.get("survey_id")

            if not effective_survey_id:
                return (
                    "No survey ID provided. Please provide a survey_id or use the search tool to find a survey first.",
                    {
                        "error": "no_survey_id",
                        "details": "No survey_id argument provided and none found in context",
                    },
                )

            # Fetch the survey from database
            try:
                survey = await sync_to_async(Survey.objects.get)(id=effective_survey_id, team=self._team)
            except Survey.DoesNotExist:
                return f"Survey with ID '{effective_survey_id}' not found.", {
                    "error": "not_found",
                    "details": f"No survey found with ID '{effective_survey_id}' in your team.",
                }

            survey_name = survey.name

            # Fetch responses directly from database
            responses = await self._fetch_survey_responses(survey)

            if not responses:
                return (
                    f"No open-ended responses found in survey '{survey_name}'. The survey may not have open-ended questions or no responses yet.",
                    {
                        "survey_id": str(survey.id),
                        "survey_name": survey_name,
                        "response_count": 0,
                    },
                )

            total_response_count = sum(len(group.responses or []) for group in responses)

            if total_response_count == 0:
                return f"No open-ended responses found in survey '{survey_name}' to analyze.", {
                    "survey_id": str(survey.id),
                    "survey_name": survey_name,
                    "response_count": 0,
                }

            formatted_data = self._format_responses_for_analysis(responses)

            message = dedent(f"""
                Survey: "{survey_name}"
                Total open-ended responses: {total_response_count}

                {formatted_data}

                Please analyze these survey responses and provide:
                1. Key themes with example responses
                2. Overall sentiment (positive, negative, mixed, or neutral)
                3. Actionable insights
                4. Specific recommendations based on the feedback
            """).strip()

            return message, {
                "survey_id": str(survey.id),
                "survey_name": survey_name,
                "response_count": total_response_count,
            }

        except Exception as e:
            capture_exception(e, {"team_id": self._team.id, "user_id": self._user.id})
            return f"Failed to retrieve survey responses: {str(e)}", {"error": "retrieval_failed", "details": str(e)}


SURVEY_TRANSLATE_TOOL_DESCRIPTION = dedent("""
    Use this tool to AI-translate an existing survey to another language.

    # When to use
    - User wants to translate a survey to another language
    - User mentions translating survey content to Spanish, French, etc.
    - User wants to localize a survey for different markets/regions
    - User wants to translate a specific question only
    - User wants to translate multiple specific questions
    - User wants to translate to multiple languages at once
    - User wants to translate only specific fields (e.g., just questions, not descriptions)
    - User wants to retranslate only the parts they changed (smart retranslation)
    - User wants to translate a specific field (e.g., one choice option)

    # Finding the Survey
    First use the search tool with kind="surveys" to find the survey ID, then use this tool.

    # Supported Languages
    Common languages include: English (en), Spanish (es), French (fr), German (de),
    Portuguese (pt, pt-BR, pt-PT), Chinese (zh, zh-CN, zh-TW), Japanese (ja), Korean (ko),
    Russian (ru), Arabic (ar), Hindi (hi), Italian (it), Dutch (nl), Polish (pl), Turkish (tr)

    You can also use localized variants like en-US, en-GB, es-ES, es-MX, fr-FR, fr-CA, de-DE

    # Translation Options
    - **Full survey translation**: Provide just survey_id and target_language
    - **Single question**: Use question_index (0-based) to translate one question
    - **Multiple questions**: Use question_indices array (e.g., [0, 2, 4] for questions 1, 3, 5)
    - **Multiple languages**: Use target_languages array to translate to many languages at once
    - **Specific fields**: Use fields array to translate only certain fields
      (e.g., ['question', 'choices'] to skip descriptions and button text)
    - **Smart retranslation**: Set only_changed_fields=True when base language changed and you want to update other languages efficiently
    - **Per-field targeting**: Use field_path for surgical translation of a specific field

    # Smart Retranslation
    When only_changed_fields=True, the tool detects which fields changed in the base language since last translation
    by comparing current values with _source snapshots. Only fields that changed in the base language are retranslated.
    Use this when user edited the English survey and wants to update Spanish/French/etc. efficiently.

    # Per-Field Targeting Syntax
    Use field_path parameter to translate a specific field. Examples:
    - "questions.0.question" = first question's text
    - "questions.1.description" = second question's description
    - "questions.0.choices.2" = third choice (0-indexed) in first question
    - "appearance.thankYouMessageHeader" = thank you header text

    Note: Questions and choices are 0-indexed (first question = 0, second = 1, etc.)
    When user says "question 1", convert to index 0. When they say "third choice", convert to index 2.

    # How it works
    - The tool uses AI to translate survey questions, descriptions, button text, and thank you messages
    - Translations are added to the survey's translations object
    - Original survey content remains unchanged
    - The survey editor can further refine the AI-generated translations if needed

    # Important Notes
    - Requires organization to have AI data processing approved
    - Use standard language codes (e.g., 'es' for Spanish, 'fr' for French)
    - You cannot translate a survey that doesn't belong to your team
    - The survey must be saved (have an ID) before it can be translated
    - Cannot use both question_index and question_indices at the same time
    - Smart retranslation requires previous translations with _source snapshots
```
    """).strip()


class TranslateSurveyToolArgs(BaseModel):
    survey_id: str = Field(description="UUID of the survey to translate")
    target_language: str | None = Field(
        default=None,
        description="Target language code for single-language translation (e.g., 'es', 'fr', 'de'). Use this OR target_languages, not both.",
    )
    target_languages: list[str] | None = Field(
        default=None,
        description="Array of language codes for batch translation (e.g., ['es', 'fr', 'de']). Use this OR target_language, not both.",
    )
    question_index: int | None = Field(
        default=None,
        description="Zero-based index of a specific question to translate. If provided, only that question is translated. Cannot be used with question_indices.",
    )
    question_indices: list[int] | None = Field(
        default=None,
        description="Array of question indices to translate (e.g., [0, 2, 4] for questions 1, 3, and 5). Cannot be used with question_index.",
    )
    fields: list[str] | None = Field(
        default=None,
        description="Array of field names to translate. Options: 'question', 'description', 'buttonText', 'choices', 'link', 'appearance'. If not provided, all fields are translated.",
    )
    field_path: str | None = Field(
        default=None,
        description="Specific field path for surgical translation (e.g., 'questions.0.choices.2' for third choice in first question). When provided, only this field is translated.",
    )
    only_changed_fields: bool = Field(
        default=True,
        description="Smart retranslation (enabled by default): Only retranslate fields where base language changed since last translation. Compares with _source snapshots. Set to False to force full retranslation.",
    )


class TranslateSurveyTool(MaxTool):
    name: str = "translate_survey"
    description: str = SURVEY_TRANSLATE_TOOL_DESCRIPTION
    args_schema: type[BaseModel] = TranslateSurveyToolArgs

    def get_required_resource_access(self):
        return [("survey", "editor")]

    async def is_dangerous_operation(self, **kwargs) -> bool:
        """Translating is not a dangerous operation - it just adds translations."""
        return False

    async def _arun_impl(
        self,
        survey_id: str,
        target_language: str | None = None,
        target_languages: list[str] | None = None,
        question_index: int | None = None,
        question_indices: list[int] | None = None,
        fields: list[str] | None = None,
        field_path: str | None = None,
        only_changed_fields: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """
        Translate a survey to the target language(s) using AI.
        Supports single/batch translation, per-question translation, multi-question selection,
        field filtering, smart retranslation, and per-field targeting.
        """
        # Validate parameters
        if not target_language and not target_languages:
            return "You must provide either 'target_language' or 'target_languages'.", {
                "error": "invalid_params",
                "details": "Missing target language(s)",
            }

        if target_language and target_languages:
            return "Provide either 'target_language' or 'target_languages', not both.", {
                "error": "invalid_params",
                "details": "Cannot use both single and batch translation modes",
            }

        if question_index is not None and question_indices is not None:
            return "Provide either 'question_index' or 'question_indices', not both.", {
                "error": "invalid_params",
                "details": "Cannot use both single and multi-question modes",
            }

        try:
            from products.llm_analytics.backend.translation.llm import translate_text

            team = self._team
            user = self._user

            # Check if AI data processing is approved
            if not self._organization.is_ai_data_processing_approved:
                return (
                    "AI data processing must be approved by your organization to use the translation feature.",
                    {"error": "permission_denied", "details": "AI data processing not approved for this organization"},
                )

            # Fetch the existing survey
            try:
                survey = await sync_to_async(Survey.objects.get)(id=survey_id, team=team)
            except Survey.DoesNotExist:
                return f"Survey with ID '{survey_id}' not found.", {
                    "error": "not_found",
                    "details": f"No survey found with ID '{survey_id}' in your team.",
                }

            survey_name = survey.name

            # Helper to check if a field should be translated
            def should_translate_field(field_name: str) -> bool:
                return fields is None or field_name in fields

            # Handle per-field targeting (uses translate_field endpoint)
            if field_path:
                if not target_language:
                    return "Per-field targeting requires a single target_language, not target_languages.", {
                        "error": "invalid_params",
                        "details": "Use target_language with field_path",
                    }

                # Parse field path (e.g., "questions.0.choices.2")
                try:
                    result = await self._translate_field(survey, field_path, target_language, user)

                    await sync_to_async(self._report_user_action)("per-field survey translation generated")

                    return f"Field '{field_path}' in survey '{survey_name}' translated to {target_language}!", {
                        "survey_id": survey_id,
                        "survey_name": survey_name,
                        "field_path": field_path,
                        "target_language": target_language,
                        "translation": result,
                    }
                except Exception as e:
                    return f"Failed to translate field: {str(e)}", {
                        "error": "translation_failed",
                        "details": str(e),
                    }

            # If batch translation to multiple languages
            if target_languages:
                all_translations = {}
                errors = {}

                for lang in target_languages:
                    try:
                        lang_translations = await self._translate_survey(
                            survey,
                            lang,
                            user,
                            question_index,
                            question_indices,
                            should_translate_field,
                            only_changed_fields,
                        )
                        all_translations[lang] = lang_translations
                    except Exception as e:
                        errors[lang] = str(e)

                success_count = len(all_translations)
                error_count = len(errors)

                await sync_to_async(self._report_user_action)("batch survey translation generated")

                message = f"Survey '{survey_name}' translated to {success_count} language(s)"
                if error_count > 0:
                    message += f" ({error_count} failed)"

                return message, {
                    "survey_id": survey_id,
                    "survey_name": survey_name,
                    "translations": all_translations,
                    "errors": errors,
                }

            # Single language translation
            target_lang = target_language or target_languages[0]  # type: ignore
            translations = await self._translate_survey(
                survey, target_lang, user, question_index, question_indices, should_translate_field, only_changed_fields
            )

            await sync_to_async(self._report_user_action)("survey translation generated")

            # Build descriptive message
            if question_indices:
                question_msg = f" (questions {', '.join(str(i + 1) for i in question_indices)})"
            elif question_index is not None:
                question_msg = f" (question {question_index + 1})"
            else:
                question_msg = ""

            smart_msg = " (smart retranslation)" if only_changed_fields else ""

            return f"Survey '{survey_name}'{question_msg} successfully translated to {target_lang}{smart_msg}!", {
                "survey_id": survey_id,
                "survey_name": survey_name,
                "target_language": target_lang,
                "question_index": question_index,
                "question_indices": question_indices,
                "only_changed_fields": only_changed_fields,
                "translations": translations,
            }

            # Translate each question
            for question in survey.questions:
                question_translation: dict[str, Any] = {}

                if "question" in question:
                    question_translation["question"] = await sync_to_async(translate_text)(
                        question["question"], target_language, user_distinct_id=user.distinct_id
                    )

                if "description" in question:
                    question_translation["description"] = await sync_to_async(translate_text)(
                        question["description"], target_language, user_distinct_id=user.distinct_id
                    )

                if "buttonText" in question:
                    question_translation["buttonText"] = await sync_to_async(translate_text)(
                        question["buttonText"], target_language, user_distinct_id=user.distinct_id
                    )

                if "choices" in question and isinstance(question["choices"], list):
                    choices_translation = []
                    for choice in question["choices"]:
                        translated_choice = await sync_to_async(translate_text)(
                            choice, target_language, user_distinct_id=user.distinct_id
                        )
                        choices_translation.append(translated_choice)
                    question_translation["choices"] = choices_translation

                if "link" in question:
                    question_translation["link"] = await sync_to_async(translate_text)(
                        question["link"], target_language, user_distinct_id=user.distinct_id
                    )

                translations["questions"].append(question_translation)

            # Translate appearance (thank you message)
            appearance = survey.appearance or {}
            appearance_translation: dict[str, Any] = {}

            if "thankYouMessageHeader" in appearance:
                appearance_translation["thankYouMessageHeader"] = await sync_to_async(translate_text)(
                    appearance["thankYouMessageHeader"], target_language, user_distinct_id=user.distinct_id
                )

            if "thankYouMessageDescription" in appearance:
                appearance_translation["thankYouMessageDescription"] = await sync_to_async(translate_text)(
                    appearance["thankYouMessageDescription"], target_language, user_distinct_id=user.distinct_id
                )

            if "thankYouMessageCloseButtonText" in appearance:
                appearance_translation["thankYouMessageCloseButtonText"] = await sync_to_async(translate_text)(
                    appearance["thankYouMessageCloseButtonText"], target_language, user_distinct_id=user.distinct_id
                )

            if appearance_translation:
                translations["appearance"] = appearance_translation

            # Report user action
            await sync_to_async(self._report_user_action)("survey translation generated")

            return f"Survey '{survey_name}' successfully translated to {target_language}!", {
                "survey_id": survey_id,
                "survey_name": survey_name,
                "target_language": target_language,
                "translations": translations,
            }

        except Exception as e:
            capture_exception(e, {"team_id": self._team.id, "user_id": self._user.id})
            return f"Failed to translate survey: {str(e)}", {"error": "translation_failed", "details": str(e)}

    async def _translate_survey(
        self,
        survey: Survey,
        target_language: str,
        user: Any,
        question_index: int | None,
        question_indices: list[int] | None,
        should_translate_field: Any,
        only_changed_fields: bool = False,
    ) -> dict[str, Any]:
        """Helper method to translate a survey to a single language."""
        from products.llm_analytics.backend.translation.llm import translate_text

        translations: dict[str, Any] = {}

        # Determine which questions to translate
        if question_indices is not None:
            # Multi-question selection
            questions_to_translate = [survey.questions[i] for i in question_indices if i < len(survey.questions)]
            questions_indices = question_indices
        elif question_index is not None:
            # Single question
            questions_to_translate = [survey.questions[question_index]]
            questions_indices = [question_index]
        else:
            # All questions
            questions_to_translate = survey.questions
            questions_indices = list(range(len(survey.questions)))

        # Get existing translations for smart retranslation
        existing_translations = {}
        if only_changed_fields and survey.translations:
            existing_translations = survey.translations.get(target_language, {})

        # Translate questions
        if questions_to_translate:
            translated_questions = []
            for _idx, (question, q_idx) in enumerate(zip(questions_to_translate, questions_indices)):
                question_translation: dict[str, Any] = {}

                # Get existing translation and _source snapshot for this question
                existing_q = {}
                current_source_snapshot = {}
                if only_changed_fields and existing_translations.get("questions"):
                    if q_idx < len(existing_translations["questions"]):
                        existing_q = existing_translations["questions"][q_idx]
                        current_source_snapshot = existing_q.get("_source", {})

                # Helper to check if field changed (for smart retranslation)
                def field_changed(field_name: str, current_value: str | None, snapshot=current_source_snapshot) -> bool:
                    if not only_changed_fields or not snapshot:
                        return True  # Translate everything if not smart mode or no snapshot
                    return snapshot.get(field_name) != current_value

                if "question" in question and should_translate_field("question"):
                    if field_changed("question", question.get("question")):
                        question_translation["question"] = await sync_to_async(translate_text)(
                            question["question"], target_language, user_distinct_id=user.distinct_id
                        )
                        # ALWAYS save snapshot when translating (not just when only_changed_fields=False)
                        question_translation.setdefault("_source", {})["question"] = question["question"]
                    elif existing_q.get("question"):
                        # Preserve existing translation AND its snapshot
                        question_translation["question"] = existing_q["question"]
                        if existing_q.get("_source", {}).get("question"):
                            question_translation.setdefault("_source", {})["question"] = existing_q["_source"][
                                "question"
                            ]

                if "description" in question and should_translate_field("description"):
                    if field_changed("description", question.get("description")):
                        question_translation["description"] = await sync_to_async(translate_text)(
                            question["description"], target_language, user_distinct_id=user.distinct_id
                        )
                        question_translation.setdefault("_source", {})["description"] = question["description"]
                    elif existing_q.get("description"):
                        question_translation["description"] = existing_q["description"]
                        if existing_q.get("_source", {}).get("description"):
                            question_translation.setdefault("_source", {})["description"] = existing_q["_source"][
                                "description"
                            ]

                if "buttonText" in question and should_translate_field("buttonText"):
                    if field_changed("buttonText", question.get("buttonText")):
                        question_translation["buttonText"] = await sync_to_async(translate_text)(
                            question["buttonText"], target_language, user_distinct_id=user.distinct_id
                        )
                        question_translation.setdefault("_source", {})["buttonText"] = question["buttonText"]
                    elif existing_q.get("buttonText"):
                        question_translation["buttonText"] = existing_q["buttonText"]
                        if existing_q.get("_source", {}).get("buttonText"):
                            question_translation.setdefault("_source", {})["buttonText"] = existing_q["_source"][
                                "buttonText"
                            ]

                if (
                    "choices" in question
                    and isinstance(question["choices"], list)
                    and should_translate_field("choices")
                ):
                    choices_str = ",".join(question["choices"])
                    if field_changed("choices", choices_str):
                        choices_translation = []
                        for choice in question["choices"]:
                            translated_choice = await sync_to_async(translate_text)(
                                choice, target_language, user_distinct_id=user.distinct_id
                            )
                            choices_translation.append(translated_choice)
                        question_translation["choices"] = choices_translation
                        question_translation.setdefault("_source", {})["choices"] = choices_str
                    elif existing_q.get("choices"):
                        question_translation["choices"] = existing_q["choices"]
                        if existing_q.get("_source", {}).get("choices"):
                            question_translation.setdefault("_source", {})["choices"] = existing_q["_source"]["choices"]

                if "link" in question and should_translate_field("link"):
                    if field_changed("link", question.get("link")):
                        question_translation["link"] = await sync_to_async(translate_text)(
                            question["link"], target_language, user_distinct_id=user.distinct_id
                        )
                        question_translation.setdefault("_source", {})["link"] = question["link"]
                    elif existing_q.get("link"):
                        question_translation["link"] = existing_q["link"]
                        if existing_q.get("_source", {}).get("link"):
                            question_translation.setdefault("_source", {})["link"] = existing_q["_source"]["link"]

                translated_questions.append(question_translation)

            translations["questions"] = translated_questions

        # Translate appearance (thank you message) if not doing per-question translation
        if question_index is None and question_indices is None and should_translate_field("appearance"):
            appearance = survey.appearance or {}
            appearance_translation: dict[str, Any] = {}

            # Get existing appearance translation for smart retranslation
            existing_appearance = {}
            appearance_source = {}
            if only_changed_fields and existing_translations.get("appearance"):
                existing_appearance = existing_translations["appearance"]
                appearance_source = existing_appearance.get("_source", {})

            def appearance_field_changed(field_name: str, current_value: str | None) -> bool:
                if not only_changed_fields or not appearance_source:
                    return True
                return appearance_source.get(field_name) != current_value

            if "thankYouMessageHeader" in appearance:
                if appearance_field_changed("thankYouMessageHeader", appearance.get("thankYouMessageHeader")):
                    appearance_translation["thankYouMessageHeader"] = await sync_to_async(translate_text)(
                        appearance["thankYouMessageHeader"], target_language, user_distinct_id=user.distinct_id
                    )
                    appearance_translation.setdefault("_source", {})["thankYouMessageHeader"] = appearance[
                        "thankYouMessageHeader"
                    ]
                elif existing_appearance.get("thankYouMessageHeader"):
                    appearance_translation["thankYouMessageHeader"] = existing_appearance["thankYouMessageHeader"]
                    if existing_appearance.get("_source", {}).get("thankYouMessageHeader"):
                        appearance_translation.setdefault("_source", {})["thankYouMessageHeader"] = existing_appearance[
                            "_source"
                        ]["thankYouMessageHeader"]

            if "thankYouMessageDescription" in appearance:
                if appearance_field_changed("thankYouMessageDescription", appearance.get("thankYouMessageDescription")):
                    appearance_translation["thankYouMessageDescription"] = await sync_to_async(translate_text)(
                        appearance["thankYouMessageDescription"], target_language, user_distinct_id=user.distinct_id
                    )
                    appearance_translation.setdefault("_source", {})["thankYouMessageDescription"] = appearance[
                        "thankYouMessageDescription"
                    ]
                elif existing_appearance.get("thankYouMessageDescription"):
                    appearance_translation["thankYouMessageDescription"] = existing_appearance[
                        "thankYouMessageDescription"
                    ]
                    if existing_appearance.get("_source", {}).get("thankYouMessageDescription"):
                        appearance_translation.setdefault("_source", {})["thankYouMessageDescription"] = (
                            existing_appearance["_source"]["thankYouMessageDescription"]
                        )

            if "thankYouMessageCloseButtonText" in appearance:
                if appearance_field_changed(
                    "thankYouMessageCloseButtonText", appearance.get("thankYouMessageCloseButtonText")
                ):
                    appearance_translation["thankYouMessageCloseButtonText"] = await sync_to_async(translate_text)(
                        appearance["thankYouMessageCloseButtonText"], target_language, user_distinct_id=user.distinct_id
                    )
                    appearance_translation.setdefault("_source", {})["thankYouMessageCloseButtonText"] = appearance[
                        "thankYouMessageCloseButtonText"
                    ]
                elif existing_appearance.get("thankYouMessageCloseButtonText"):
                    appearance_translation["thankYouMessageCloseButtonText"] = existing_appearance[
                        "thankYouMessageCloseButtonText"
                    ]
                    if existing_appearance.get("_source", {}).get("thankYouMessageCloseButtonText"):
                        appearance_translation.setdefault("_source", {})["thankYouMessageCloseButtonText"] = (
                            existing_appearance["_source"]["thankYouMessageCloseButtonText"]
                        )

            if appearance_translation:
                translations["appearance"] = appearance_translation

        return translations

    async def _translate_field(
        self,
        survey: Survey,
        field_path: str,
        target_language: str,
        user: Any,
    ) -> str:
        """Helper method to translate a specific field using field path."""
        from products.llm_analytics.backend.translation.llm import translate_text

        # Parse field path (e.g., "questions.0.choices.2" or "appearance.thankYouMessageHeader")
        parts = field_path.split(".")

        if len(parts) < 2:
            raise ValueError(f"Invalid field path: {field_path}")

        # Navigate to the field value
        if parts[0] == "questions":
            if len(parts) < 3:
                raise ValueError(f"Question field path must include index and field name: {field_path}")

            q_index = int(parts[1])
            if q_index >= len(survey.questions):
                raise ValueError(f"Question index {q_index} out of range")

            question = survey.questions[q_index]
            field_name = parts[2]

            if field_name == "choices" and len(parts) == 4:
                # Specific choice: questions.0.choices.2
                choice_index = int(parts[3])
                if "choices" not in question or choice_index >= len(question["choices"]):
                    raise ValueError(f"Choice index {choice_index} out of range in question {q_index}")
                field_value = question["choices"][choice_index]
            elif field_name in question:
                # Question field: questions.0.question
                field_value = question[field_name]
            else:
                raise ValueError(f"Field '{field_name}' not found in question {q_index}")

        elif parts[0] == "appearance":
            if len(parts) != 2:
                raise ValueError(f"Appearance field path must be: appearance.fieldName")

            appearance = survey.appearance or {}
            field_name = parts[1]

            if field_name not in appearance:
                raise ValueError(f"Field '{field_name}' not found in appearance")

            field_value = appearance[field_name]

        else:
            raise ValueError(f"Unknown root field: {parts[0]}. Use 'questions' or 'appearance'")

        # Translate the field value
        translated_value = await sync_to_async(translate_text)(
            field_value, target_language, user_distinct_id=user.distinct_id
        )

        return translated_value
