# Max AI Research - Auto-Translation Feasibility for Surveys

> ⚠️ **DISCLAIMER**: This is a preliminary research document. Not all information documented here has been verified as completely accurate. The findings should be validated during implementation. Use this as a starting point for investigation, not as absolute truth.

## What is Max AI?

Max AI (PostHog AI) is PostHog's built-in AI assistant that helps users across multiple product areas:

- **Survey Analysis**: Analyzing survey responses, extracting themes, sentiment
- **Survey Creation**: Creating surveys from natural language instructions
- **Experiment Analysis**: Understanding A/B test results (Bayesian & Frequentist)
- **Feature Flag Creation**: Creating and managing feature flags
- **Error Tracking**: Explaining error tracking issues
- **Query Generation**: Generating HogQL queries
- **Documentation Search**: Finding relevant PostHog docs
- **And more**: Session replay analysis, workflows, dashboards, etc.

## Current Translation Capabilities

### ✅ LLM Analytics Translation API Already Exists!

Found at `products/llm_analytics/backend/api/translate.py`:

```python
POST /api/environments/:id/llm_analytics/translate/

# Request
{
    "text": "Text to translate",
    "target_language": "es"  # Optional, defaults to "en"
}

# Response
{
    "translation": "Translated text",
    "detected_language": null,
    "provider": "openai"
}
```

**How it works:**

- Uses OpenAI's GPT model (defined in `TRANSLATION_MODEL` constant)
- Simple system prompt: "You are a translator. Translate to {language}. Only return translation, preserve formatting."
- Currently used for LLM Analytics traces/messages
- Has rate limiting built-in:
  - `LLMAnalyticsTranslationBurstThrottle`
  - `LLMAnalyticsTranslationSustainedThrottle`
  - `LLMAnalyticsTranslationDailyThrottle`

**Implementation:**

```python
# products/llm_analytics/backend/translation/llm.py
def translate_text(text: str, target_language: str) -> str:
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30.0)
    target_name = SUPPORTED_LANGUAGES.get(target_language, target_language)

    response = client.chat.completions.create(
        model=TRANSLATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": f"You are a translator. Translate the following text to {target_name}. "
                "Only return the translation, nothing else. Preserve formatting and line breaks.",
            },
            {"role": "user", "content": text},
        ],
        user="llma-translation",
    )
    return response.choices[0].message.content.strip()
```

## Billing & Pricing

### 🎯 Free Tier & Usage Model

**Default Free Tier:**

- **2,000 credits per month** (defined in `DEFAULT_FREE_TIER_CREDITS`)
- Can be customized per team via feature flags
- GA launch date: Nov 17, 2025 (usage before this not counted)

**Credit System:**

- Max AI uses a "credits" system for billing
- Each LLM generation costs credits based on tokens + markup
- **20% markup** on top of base LLM cost (`AI_COST_MARKUP_PERCENT = 0.2`)
- Billable flag on tools: `billable=True` marks a tool's LLM calls as billable

**Checking Usage:**
Users can check their AI usage via `/usage` slash command:

```text
/usage
```

This shows:

- Current conversation credits used
- Past 30 days credits used
- Free tier limit
- Progress bar showing % of free tier used
- Remaining credits or overage

**Exemptions:**

- Some tools excluded from billing: `["summarize_sessions", "search"]`
- Impersonated sessions not billable (workflow-level override)

### 📊 How Billing Works

From `ee/hogai/llm.py`:

```python
class MaxChatMixin(BaseModel):
    billable: bool = False
    """
    Whether the generation will be marked as billable in the usage report
    for calculating AI billing credits.
    """

    def _get_effective_billable(self) -> bool:
        """
        Determine the effective billable status for this generation.
        Combines model-level billable setting with workflow-level override.
        """
        config = ensure_config()
        is_agent_billable = (config.get("configurable") or {}).get("is_agent_billable", True)
        return self.billable and is_agent_billable
```

**Key Points:**

- Tools must explicitly set `billable=True` to charge credits
- Survey creation tool currently has `billable=True`
- Survey analysis tool has `billable=True`
- Translation API has rate limiting but unclear if billable

### 🔐 Requirements

**Before using any Max AI feature:**

1. User must be authenticated
2. Organization must approve AI data processing: `organization.is_ai_data_processing_approved`
3. Must have `OPENAI_API_KEY` configured (backend setting)

## Survey-Related Max AI Tools

### 1. CreateSurveyTool

**Location:** `products/surveys/backend/max_tools.py`

**What it does:**

- Creates surveys from natural language instructions
- Example: "Create an NPS survey for users who viewed pricing page"
- Handles feature flag targeting, question types, branching
- Can launch immediately or save as draft
- Marked as `billable=True`

**Example usage in Max chat:**

```text
"Create a survey to ask users about their experience with the new dashboard"
```

### 2. SurveyAnalysisTool

**Location:** `products/surveys/backend/max_tools.py`

**What it does:**

- Analyzes open-ended survey responses
- Extracts themes, sentiment, actionable insights
- Groups similar responses
- Marked as `billable=True`

**Context available:** Survey data automatically provided from context

## 🚀 Feasibility Assessment: Auto-Translation for Surveys

### ✅ HIGHLY FEASIBLE - Here's Why:

1. **Translation Infrastructure Already Exists**
   - LLM Analytics has working translation API
   - Can be reused or adapted for surveys
   - Already has rate limiting, error handling

2. **Survey Integration Points Available**
   - Survey creation tool can be extended
   - Could add "translate survey" tool
   - Context system already provides survey data to Max AI

3. **Multiple Implementation Approaches:**

#### Option A: New MaxTool for Survey Translation

```python
class TranslateSurveyTool(MaxTool):
    name: str = "translate_survey"
    description: str = "Translate survey content to another language"
    billable: bool = True  # Mark as billable

    async def _arun_impl(self, survey_id: str, target_languages: list[str]):
        # 1. Fetch survey
        # 2. For each target language:
        #    - Translate name, description
        #    - Translate each question
        #    - Translate choices
        #    - Translate thank you message
        # 3. Save translations
        # 4. Return success message
```

#### Option B: Extend Existing Translation API

```python
# New endpoint in surveys backend
POST /api/environments/:id/surveys/:survey_id/translate/

{
    "target_languages": ["es", "fr", "de"],
    "fields": ["all"]  # or specific: ["questions", "choices"]
}
```

#### Option C: Button in UI → Max AI Chat

- Add "Auto-translate with AI" button in Translations tab
- Opens Max AI side panel with pre-filled prompt
- User can review and approve before saving
- Could use dangerous operation approval system

### 💡 Recommended Implementation

**Phase 1: Manual Workflow (Quick Win)**

1. Add button in Translations tab: "Translate with AI"
2. Opens Max AI chat with context
3. User types: "Translate this survey to Spanish"
4. Max AI:
   - Has survey context automatically
   - Calls translation API for each field
   - Formats response with all translations
   - User copies/pastes or auto-fills form

**Phase 2: Semi-Automated Tool (Best UX)**

1. Create `TranslateSurveyTool` as dangerous operation
2. When user adds new language, offer AI translation
3. Shows preview of all translations
4. User approves → translations saved
5. Marked as billable operation

**Phase 3: Batch Translation (Power Users)**

1. "Translate to multiple languages" button
2. Select target languages
3. Max AI translates all at once
4. Review interface to approve/edit
5. Bulk save

### 📋 Implementation Checklist

**Backend:**

- [ ] Create `TranslateSurveyTool` in `products/surveys/backend/max_tools.py`
- [ ] Reuse translation logic from LLM Analytics
- [ ] Add context formatting for survey fields
- [ ] Mark as billable operation
- [ ] Add rate limiting (reuse existing throttles)
- [ ] Add to survey toolkit registry
- [ ] Handle translation of all field types:
  - [ ] Survey name & description
  - [ ] Question text & descriptions
  - [ ] Choices (preserve structure)
  - [ ] Button labels
  - [ ] Thank you message (all 3 fields)
  - [ ] Rating labels (lower/upper bound)

**Frontend:**

- [ ] Add "Translate with AI" button in Translations tab
- [ ] Integrate with Max AI side panel
- [ ] Show translation preview/approval UI
- [ ] Handle bulk language selection
- [ ] Show credit cost estimate before translating
- [ ] Loading states during translation

**Testing:**

- [ ] Test with different survey types (NPS, multi-question, etc.)
- [ ] Test with different languages
- [ ] Test choice array synchronization
- [ ] Test validation after translation
- [ ] Test credit billing
- [ ] Test rate limiting

### 💰 Cost Implications

**For Customers:**

- Charged against their 2,000 free monthly credits
- Each survey field translation ~ 50-200 tokens
- Full survey translation (5 questions) ~ 500-1000 tokens
- Rough estimate: **50-100 credits per language** for average survey
- Users can translate **20-40 surveys per month** within free tier
- Additional usage charged based on token usage + 20% markup

**Value Proposition:**

- Manual translation: 30-60 minutes per language
- AI translation: 10-30 seconds per language
- Massive time savings for global products
- Can translate to 10+ languages in minutes
- Only pay for what you use (within free tier first)

## 🎓 Learning from Existing Tools

**Survey Creation Tool Pattern:**

```python
class CreateSurveyTool(MaxTool):
    billable: bool = False
    context_prompt_template: str = "You can create surveys..."

    async def _arun_impl(self, instructions: str) -> tuple[str, dict]:
        # 1. Use LangGraph to understand instructions
        # 2. Create survey schema
        # 3. Validate and save
        # 4. Return success message + survey_id

        return f"✅ Survey created!", {"survey_id": survey.id}
```

**Translation could follow same pattern:**

```python
class TranslateSurveyTool(MaxTool):
    billable: bool = True  # Important: charge credits
    context_prompt_template: str = "Survey data: {survey_json}"

    async def _arun_impl(self, target_language: str) -> tuple[str, dict]:
        # 1. Get survey from context
        # 2. Translate all fields
        # 3. Validate translations
        # 4. Save to survey.translations
        # 5. Return summary

        return f"✅ Translated to {target_language}!", {
            "survey_id": survey_id,
            "language": target_language,
            "fields_translated": 15
        }
```

## 🔍 Additional Findings

### Max AI Capabilities with Surveys Currently:

1. **Create surveys** from natural language
2. **Analyze survey responses** (open-ended questions)
3. **Feature flag targeting** for surveys
4. Has **context awareness** of survey data
5. Can **suggest survey improvements**

### What's NOT Possible Yet:

1. ❌ Auto-translation (what we want to build!)
2. ❌ Translation quality validation
3. ❌ Terminology management (glossaries)
4. ❌ Translation memory (reuse previous translations)

## 🎯 Recommendation

**YES - This is absolutely feasible and makes sense!**

**Reasons to proceed:**

1. ✅ Translation infrastructure exists and works well
2. ✅ Max AI already understands surveys deeply
3. ✅ Billing system supports this use case
4. ✅ Free tier generous enough for meaningful usage
5. ✅ Clear customer value (save hours of manual work)
6. ✅ Fits naturally into existing Max AI product

**Suggested Next Steps:**

1. Build Phase 1 (manual workflow) - **1-2 days**
   - Low risk, immediate value
   - Test customer interest
2. Gather feedback, then build Phase 2 - **3-5 days**
   - Proper tool integration
   - Approval workflow
   - Billing integration

3. Monitor usage and iterate - **Ongoing**
   - Track credit usage
   - Improve translation quality
   - Add features (glossaries, etc.)

**Total Effort:** ~1 week for MVP, 2 weeks for polished feature

---

## 📚 Key Files to Review

- `products/llm_analytics/backend/api/translate.py` - Translation API
- `products/llm_analytics/backend/translation/llm.py` - Translation logic
- `products/surveys/backend/max_tools.py` - Survey Max tools
- `ee/hogai/tool.py` - Base MaxTool class
- `ee/hogai/llm.py` - Billing and credit tracking
- `ee/hogai/chat_agent/slash_commands/commands/usage/` - Usage tracking

## 🤝 Questions?

Feel free to ask about:

- Specific implementation details
- Billing calculation examples
- Integration with existing translation validation
- Handling of special survey field types
- Testing strategies
