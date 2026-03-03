# 🤖 AI Survey Translation - Complete Feature Guide

> **What it does:** Instantly translate your survey into any language using AI - from full survey translation to per-field editing with hover wand icons. Available via UI or Max AI chat.

---

## Prerequisites

**Before starting:**

1. Organization Settings → Enable "AI data processing" (admin only)
2. Have a saved survey (you CAN translate drafts via UI)

---

## Translation Methods

You can translate surveys in two ways:

1. **UI Magic Wand** - Full control with visual feedback, supports drafts
2. **Max AI Chat** - Natural language commands (REQUIRES saved survey with ID)

---

## Demo Flow

### 1. Create Base Survey

**Create a new survey** with this content:

```text
Name: Product Feedback Survey
Description: Help us improve

Question 1 (Rating):
  Question: "How satisfied are you?"
  Description: "Rate your experience"
  Lower Label: "Not satisfied"
  Upper Label: "Very satisfied"

Question 2 (Multiple Choice):
  Question: "Which features do you use?"
  Choices:
    - Analytics
    - Session Replay
    - Feature Flags

Question 3 (Open Text):
  Question: "What should we improve?"
  Button Text: "Submit"

Thank You Message (in Appearance tab):
  Header: "Thank you!"
  Description: "We'll review your feedback"
  Close Button Text: "Close"
```

**Save the survey** (as draft or launch it).

---

### 2. Add Spanish Translation with AI

1. Click **"Translations"** tab
2. Type "Spanish" or "es" in the language dropdown → Select "Spanish (es)"
3. See the language appear in the list with a **magic wand icon** ✨
4. **Click the magic wand icon**

**What happens:**

- Loading spinner appears
- Toast: "Translating survey to Spanish..."
- Wait ~3-5 seconds
- Toast: "Survey automatically translated to Spanish"

---

### 3. Review Translation

1. **Click on "Spanish (es)"** to view it
2. See translated content:

```text
Name: Encuesta de Comentarios del Producto
Description: Ayúdanos a mejorar

Question 1: "¿Qué tan satisfecho estás?"
Description: "Califica tu experiencia"
Lower: "No satisfecho"
Upper: "Muy satisfecho"

Question 2: "¿Qué funciones usas?"
Choices:
  - Analítica
  - Repetición de Sesión
  - Banderas de Funciones

Question 3: "¿Qué deberíamos mejorar?"
Button: "Enviar"

Thank You:
  Header: "¡Gracias!"
  Description: "Revisaremos tus comentarios"
  Button: "Cerrar"
```

3. **Edit any field** if needed (translations are editable)
4. Save the survey

---

### 4. Translate Multiple Languages

1. Add "French (fr)" → Click magic wand ✨
2. Add "German (de)" → Click magic wand ✨
3. Add "Portuguese - Brazil (pt-BR)" → Click magic wand ✨

**Note:** You can click all magic wands quickly - they translate simultaneously!

---

### 5. Use Max AI Chat

**Alternative way to translate surveys:**

1. On the Surveys list page, click the **Max AI chat button** (top right)
2. Type: "Translate the Product Feedback Survey to French"
3. Max AI searches for the survey and translates it automatically
4. You can also request multiple languages: "Translate it to German and Japanese too"

---

## Using Max AI Chat for Translation

**Example Conversations:**

**Basic translation:**

```text
You: "Translate the Product Feedback Survey to Spanish"
Max AI: [Searches for survey] → [Translates to Spanish]
        "Survey 'Product Feedback Survey' successfully translated to Spanish!"
```

**Multiple languages:**

```text
You: "Translate my NPS survey to French and German"
Max AI: [Searches for NPS survey]
        → [Translates to French]
        → [Translates to German]
        "Translations complete!"
```

**With language variants:**

```text
You: "Translate the onboarding survey to Brazilian Portuguese"
Max AI: [Uses pt-BR code for Brazilian variant]
```

**Supported chat patterns:**

- "Translate [survey name] to [language]"
- "Convert [survey] to [language]"
- "Localize [survey] for [market/language]"
- Handles 30+ languages including variants

---

## What Gets Translated

✅ **Translated:**

- Survey name & description
- Question text & descriptions
- Multiple choice options
- Button text
- Rating labels (lower/upper bound)
- Link display text
- Thank you message (header, description, close button)

❌ **Not translated:**

- Question types
- Link URLs (only display text)
- Targeting/logic rules
- Colors/styling

---

## Current Limitations

**Granularity:**

- ✅ **BASE branch:** Translates entire survey (all-or-nothing per language)
- ✅ **GRANULAR branch:** Can translate individual questions or batch of questions
- ✅ **PER-FIELD branch:** Can translate individual fields (e.g., just one choice option)
- 💡 _Feature evolution:_ Each branch adds more surgical translation capabilities---

## Max AI Chat Capabilities vs UI Features

**⚠️ Important:** Max AI chat has limited capabilities compared to the UI:

### What Max AI Chat CAN Do ✅

- Translate saved surveys (requires survey_id)
- Single language translation: "Translate Product Feedback Survey to Spanish"
- Multiple languages batch: "Translate it to French, German, and Japanese"
- Per-question translation: "Translate just question 2 to Spanish"
- Field filtering: "Translate only the question text to French" (skips descriptions/buttons)
- Supported fields: question, description, buttonText, choices, link, appearance

### What Max AI Chat CANNOT Do ❌

- **Draft translation**: Requires saved survey with ID (no `survey_data` parameter in tool)
- **Smart retranslation**: Cannot pass `only_changed_fields` parameter (no \_source snapshot access)
- **Multi-question selection**: Only has `question_index` (single int), not `question_indices` array
- **Per-field translation**: No equivalent of hover wand icon endpoint for surgical field edits

### Why These Limitations?

```python
# TranslateSurveyToolArgs in max_tools.py
class TranslateSurveyToolArgs(BaseModel):
    survey_id: str  # REQUIRES saved survey (no survey_data support)
    target_language: str | None
    target_languages: list[str] | None
    question_index: int | None  # Single question only
    fields: list[str] | None
    # MISSING: only_changed_fields, survey_data, question_indices array
```

**Translation API supports:**

- `survey` parameter (dict) - for draft translation
- `only_changed_fields` (bool) - for smart retranslation
- Both single question and question indices array

**Max AI tool only exposes:**

- `survey_id` (str) - saved surveys only
- `question_index` (int) - single question
- No smart retranslation parameter

---

## Feature Branches & Commit Breakdown

This feature is developed across 4 progressive branches with 18 total commits (with 1 duplicate/reworked):

### 1. `feat/surveys-ai-translations` (BASE - 4 commits)

**Commits:**

1. `746a8da5ba` - AI-powered auto-translation
2. `45f3c416f4` - Comprehensive tests for AI translation endpoint
3. `a745055054` - Max AI chat integration
4. `7a93808f06` - Support draft translation and fix race condition

**What it has:**

- Auto-translation of entire survey (all-or-nothing)
- Magic wand button in UI (language dropdown)
- Max AI chat tool with survey search
- Draft translation via `survey` parameter in POST body
- Single translation endpoint (`/api/projects/:id/surveys/:survey_id/translate/`)
- Test coverage (`TestSurveyTranslation` - basic tests)

**API endpoints:**

- POST `/translate/` - Main translation endpoint (entire survey only)

**Use case:** Basic translation - entire survey at once, single language

**Note:** The draft translation commit (7a93808f06) was reworked in GRANULAR as a6a411b31b

### 2. `feat/surveys-ai-translations-granular` (+7 commits)

**Commits:**

5. `fe58ac743c` - Granular translation features (per-question, batch, field filtering)
6. `c653d22603` - DRF serializers for translation validation
7. `3b12db0d7d` - Frontend actions and API methods for granular translation
8. `1321510439` - Granular translation UI components
9. `bc8d9a3adf` - Update Max AI tool for granular translations
10. `e9679ee02a` - Update tests to match DRF serializer error response format
11. `f9c367293d` - Multi-question selection UI (checkboxes)

**What it adds:**

- Per-question translation endpoint (`/translate_question/:index/`)
- Batch translation endpoint (`/translate_batch/`) for multiple languages at once
- Field filtering (e.g., translate only `question` and `choices`, skip descriptions)
- Multi-question checkbox selection in UI
- Question indices array support (translate questions 1, 3, 5)
- Reworked draft translation (a6a411b31b replaces BASE's 7a93808f06)
- DRF serializers for proper validation
- Updated Max AI tool to support per-question and field filtering
- Expanded test class: `TestSurveyGranularTranslation`

**New API endpoints:**

- POST `/translate_question/:index/` - Per-question translation
- POST `/translate_batch/` - Batch translate (multiple languages concurrently)

**New parameters:**

- `question_indices: list[int]` - Select multiple questions
- `fields: list[str]` - Filter which fields to translate
- `survey: dict` - Survey data for draft translation (reworked from BASE)

**Use case:** Selective translation - choose specific questions and fields, translate drafts, batch languages

**Note:** GRANULAR includes commit a6a411b31b which is a rework of BASE's draft translation (7a93808f06). For commit count purposes, GRANULAR adds 7 truly new commits + 1 reworked commit = 8 total commits on top of BASE.

### 3. `feat/surveys-ai-translations-smart-retranslation` (+3 commits)

**Commits:**

12. `8a40823c16` - Smart retranslation with Ctrl+click
13. `c00bdf11f3` - Handle None translations
14. `f808a66dfb` - Remove field filtering, add smart retranslation to all endpoints

**What it adds:**

- Smart retranslation: only translate fields that changed since last translation
- Source field tracking: `_source` snapshots in translations object
- UI behavior swap:
  - **Regular click** (default): Smart retranslation (only changed fields)
  - **Ctrl+click**: Full overwrite retranslation (all fields)
- Removes field filtering support (smart retranslation is more useful)
- New test classes: `TestSurveySmartRetranslation`, `TestSmartRetranslationOnAllEndpoints`

**New parameter:**

- `only_changed_fields: bool` - Compare with `_source` snapshots

**How it works:**

```python
# When translating, the API compares current field values with _source snapshots
existing_q = survey.translations[lang]["questions"][i]
source_snapshot = existing_q.get("_source", {})

# Only translate if field changed
if source_snapshot.get("question") != question["question"]:
    translate_text(question["question"], lang)
```

**Use case:** Efficient retranslation when English source is updated

### 4. `feat/surveys-ai-translations-per-field` (+3 commits)

**Commits:**

15. `56ca2aac6b` - Per-field translation endpoint and tests
16. `97d69bd999` - Hover-based wand icon implementation
17. `74d0b161ae` - Complete wand icon UI for appearance fields

**What it adds:**

- Per-field translation endpoint: `/translate_field/`
- Hover wand icons on individual fields (surgical translation)
- Question fields: question, description, choices (each choice), buttonText
- Appearance fields: thankYouMessageHeader, thankYouMessageDescription, thankYouMessageCloseButtonText
- New test class: `TestSurveyFieldTranslation`

**New API endpoint:**

```python
POST /api/projects/:id/surveys/:survey_id/translate_field/
{
    "field_path": "questions.0.choices.2",  # Path to specific field
    "field_value": "Analytics",  # Current English value
    "target_language": "es",  # Spanish
    "current_translation": "Analítica"  # Optional: existing translation for context
}
```

**UI behavior:**

- Hover over any translatable field → See wand icon ✨
- Click wand → Translate just that field
- Works on: question text, description, choices, button text, thank you messages

**Note:** Survey title/description don't have wand icons (SceneTitleSection is shared component, complex to modify, lower priority since they're short text)

**Use case:** Ultra-surgical translation - fix one specific field without retranslating everything

---

## Complete Feature Matrix

| Feature                  | BASE | GRANULAR      | SMART-RETRANS | PER-FIELD | Max AI Chat |
| ------------------------ | ---- | ------------- | ------------- | --------- | ----------- |
| Full survey translation  | ✅   | ✅            | ✅            | ✅        | ✅          |
| Per-question translation | ❌   | ✅            | ✅            | ✅        | ✅ (single) |
| Multi-question selection | ❌   | ✅            | ✅            | ✅        | ❌          |
| Field filtering          | ❌   | ✅            | ❌            | ✅        | ✅          |
| Smart retranslation      | ❌   | ❌            | ✅            | ✅        | ❌          |
| Per-field hover wands    | ❌   | ❌            | ❌            | ✅        | ❌          |
| Draft translation        | ✅   | ✅ (reworked) | ✅            | ✅        | ❌          |
| Batch languages          | ❌   | ✅            | ✅            | ✅        | ✅          |

---

## Testing Checklist by Branch

### BASE Branch Testing

- [ ] Enable AI data processing in org settings
- [ ] Create and save a survey
- [ ] Add Spanish → Click magic wand → Verify translation
- [ ] View translated content
- [ ] Edit one translated field manually → Save
- [ ] Add 3 more languages → Click all magic wands → Show concurrent translation
- [ ] Translate draft survey (unsaved) via UI
- [ ] Use Max AI: "Translate Product Feedback Survey to French"
- [ ] Try with unsaved survey → Show disabled button
- [ ] (Optional) Disable AI processing → Show permission error

### GRANULAR Branch Testing

All BASE tests plus:

- [ ] Select 2 questions via checkboxes → Translate
- [ ] Verify only selected questions translated
- [ ] Multi-question translation to Spanish
- [ ] Field filtering (translate only questions, skip descriptions)
- [ ] Max AI: "Translate just question 2 to German"

### SMART-RETRANS Branch Testing

All GRANULAR tests plus:

- [ ] Translate to Spanish (regular click)
- [ ] Edit English source question text
- [ ] Regular click wand → Verify only changed field retranslated
- [ ] Ctrl+click wand → Verify all fields retranslated (overwrite)
- [ ] Check `_source` snapshots in translations object
- [ ] Test with None translations (edge case)

### PER-FIELD Branch Testing

All SMART-RETRANS tests plus:

- [ ] Hover over question text → See wand icon
- [ ] Click wand → Translate just that field
- [ ] Hover over choice option → Click wand → Translate just that choice
- [ ] Hover over thank you message → Click wand
- [ ] Verify surgical translation (other fields unchanged)
- [ ] Test all appearance fields with wands

---

## Demo Flow

### 1. Create Base Survey

**Create a new survey** with this content:

```text
Name: Product Feedback Survey
Description: Help us improve

Question 1 (Rating):
  Question: "How satisfied are you?"
  Description: "Rate your experience"
  Lower Label: "Not satisfied"
  Upper Label: "Very satisfied"

Question 2 (Multiple Choice):
  Question: "Which features do you use?"
  Choices:
    - Analytics
    - Session Replay
    - Feature Flags

Question 3 (Open Text):
  Question: "What should we improve?"
  Button Text: "Submit"

Thank You Message (in Appearance tab):
  Header: "Thank you!"
  Description: "We'll review your feedback"
  Close Button Text: "Close"
```

**Save the survey** (as draft or launch it).

---

### 2. Add Spanish Translation with AI

1. Click **"Translations"** tab
2. Type "Spanish" or "es" in the language dropdown → Select "Spanish (es)"
3. See the language appear in the list with a **magic wand icon** ✨
4. **Click the magic wand icon**

**What happens:**

- Loading spinner appears
- Toast: "Translating survey to Spanish..."
- Wait ~3-5 seconds
- Toast: "Survey automatically translated to Spanish"

---

### 3. Review Translation

1. **Click on "Spanish (es)"** to view it
2. See translated content:

```text
Name: Encuesta de Comentarios del Producto
Description: Ayúdanos a mejorar

Question 1: "¿Qué tan satisfecho estás?"
Description: "Califica tu experiencia"
Lower: "No satisfecho"
Upper: "Muy satisfecho"

Question 2: "¿Qué funciones usas?"
Choices:
  - Analítica
  - Repetición de Sesión
  - Banderas de Funciones

Question 3: "¿Qué deberíamos mejorar?"
Button: "Enviar"

Thank You:
  Header: "¡Gracias!"
  Description: "Revisaremos tus comentarios"
  Button: "Cerrar"
```

3. **Edit any field** if needed (translations are editable)
4. Save the survey

---

### 4. Translate Multiple Languages (GRANULAR+ branches)

1. Add "French (fr)" → Click magic wand ✨
2. Add "German (de)" → Click magic wand ✨
3. Add "Portuguese - Brazil (pt-BR)" → Click magic wand ✨

**Note:** You can click all magic wands quickly - they translate simultaneously (batch translation)!

---

### 5. Per-Question Translation (GRANULAR+ branches)

**Use case:** Translate just one question, not the entire survey

1. Go to Italian translation (or add a new language)
2. In the question list, find **Question 2** ("Which features do you use?")
3. Click the magic wand icon **next to that specific question**
4. Wait ~2 seconds
5. Only Question 2 is translated to Italian - other questions remain untranslated

**What happened:**

- The per-question endpoint was called: `POST /translate_question/1/` (index 1 = Question 2)
- Only that question's fields were translated (question, choices)
- Other questions were not touched (efficient!)

**Max AI equivalent:**

```text
You: "Translate just question 2 of the Product Feedback Survey to Italian"
Max AI: "Survey 'Product Feedback Survey' (question 2) successfully translated to Italian!"
```

---

### 6. Multi-Question Selection (GRANULAR+ branches)

**Use case:** Translate specific questions, skip others

1. Add Japanese translation (or use existing language)
2. See **checkboxes** next to each question in the list
3. **Check Question 1 and Question 3** (skip Question 2)
4. Click the magic wand icon
5. Wait ~3 seconds
6. Only Questions 1 and 3 are translated to Japanese

**What happened:**

- Multi-question selection UI sent `question_indices: [0, 2]`
- The API translated only the selected questions
- Question 2 was skipped entirely

**Note:** This feature is UI-only - Max AI chat cannot select multiple questions at once (only has `question_index` for single question)

---

### 7. Smart Retranslation (SMART-RETRANS+ branches)

1. Edit the English source: Change "How satisfied are you?" to "How happy are you with our product?"
2. Go to Translations tab → Spanish
3. **Regular click** on magic wand (default) → Only the question text is retranslated
4. **Ctrl+click** on magic wand → All fields are retranslated (overwrite)

**Behind the scenes:**

- Each translation stores `_source` snapshots
- Regular click compares current English with `_source`
- Only changed fields are retranslated (efficient!)

---

### 8. Per-Field Translation (PER-FIELD branch only)

1. Go to Translations tab → Spanish
2. **Hover over** "¿Qué funciones usas?" → See wand icon ✨
3. Click wand → Only that question text is retranslated
4. **Hover over** the second choice "Repetición de Sesión" → See wand icon
5. Click wand → Only that choice is retranslated

**Use case:** Fix one bad translation without retranslating everything

---

### 9. Use Max AI Chat

**Alternative way to translate surveys:**

1. On the Surveys list page, click the **Max AI chat button** (top right)
2. Type: "Translate the Product Feedback Survey to French"
3. Max AI searches for the survey and translates it automatically
4. You can also request multiple languages: "Translate it to German and Japanese too"

**Max AI Chat Examples:**

```text
You: "Translate the Product Feedback Survey to Spanish"
Max AI: [Searches for survey] → [Translates to Spanish]
        "Survey 'Product Feedback Survey' successfully translated to Spanish!"
```

```text
You: "Translate my NPS survey to French and German"
Max AI: [Searches for NPS survey]
        → [Translates to French]
        → [Translates to German]
        "Survey 'NPS survey' translated to 2 language(s)"
```

```text
You: "Translate just question 2 to Japanese"
Max AI: [Searches for survey]
        "Survey 'Product Feedback Survey' (question 2) successfully translated to Japanese!"
```

**Supported chat patterns:**

- "Translate [survey name] to [language]"
- "Convert [survey] to [language]"
- "Localize [survey] for [market/language]"
- "Translate just question [N] to [language]"
- "Translate to multiple languages: French, German, Spanish"
- Handles 30+ languages including variants (pt-BR, en-US, es-MX, etc.)

---

## What Gets Translated

✅ **Translated:**

- Survey name & description
- Question text & descriptions
- Multiple choice options
- Button text
- Rating labels (lower/upper bound)
- Link display text
- Thank you message (header, description, close button)

❌ **Not translated:**

- Question types
- Link URLs (only display text)
- Targeting/logic rules
- Colors/styling

---

## Error Scenarios

**1. "Button is disabled" →** Survey not saved yet. Save first (or use draft translation in UI).

**2. "Permission denied" →** Organization hasn't enabled AI data processing.

**3. "Translation failed" →** LLM timeout. Wait 30 seconds and try again.

**4. Max AI: "Survey must be saved" →** Chat requires saved survey with ID (no draft support).

---

## Test Classes

Each branch has dedicated test classes:

1. **TestSurveyTranslation** (BASE) - Basic translation, drafts, batch, per-question
2. **TestSurveyGranularTranslation** (GRANULAR) - Multi-question selection, field filtering
3. **TestSurveySmartRetranslation** (SMART-RETRANS) - Smart retranslation feature itself
4. **TestSmartRetranslationOnAllEndpoints** (SMART-RETRANS) - Consistency across all endpoints
5. **TestSurveyFieldTranslation** (PER-FIELD) - Per-field surgical translation

**Why two test classes for smart retranslation?**

- `TestSurveySmartRetranslation`: Tests the smart retranslation feature itself
- `TestSmartRetranslationOnAllEndpoints`: Tests consistency across translate/translateBatch/translateQuestion endpoints

---

## Key Points for Video

1. **Magic wand button** is the main feature - show it clearly
2. **Toast notifications** confirm success - capture these
3. **Translations are editable** - demonstrate editing one field
4. **Multiple languages at once** - show clicking 3 magic wands quickly
5. **Per-question translation** - click wand next to single question
6. **Multi-question selection** - use checkboxes to select specific questions (GRANULAR+)
7. **Max AI Chat** - demonstrate translating via natural language
8. **Smart retranslation** (SMART-RETRANS+) - show Ctrl+click behavior
9. **Per-field wands** (PER-FIELD) - hover and click on individual fields
10. **Draft translation** - show translating unsaved survey via UI
11. **Chat limitations** - mention chat requires saved surveys, no smart retranslation

---

## Summary

**18 commits across 4 branches (with 1 reworked):**

- BASE (4): Basic auto-translation, Max AI chat integration, draft translation
- GRANULAR (+7 new, +1 reworked): Per-question/batch endpoints, field filtering, multi-question UI, reworked draft translation, DRF serializers
- SMART-RETRANS (+3): Smart retranslation with \_source tracking, Ctrl+click
- PER-FIELD (+3): Per-field endpoint, hover wand icons for surgical edits

**Note:** BASE's draft translation commit (7a93808f06) was reworked in GRANULAR (a6a411b31b), so while GRANULAR adds 8 commits, only 7 are truly new features.

**Chat vs UI:**

- UI has 100% feature coverage
- Chat missing: drafts, smart retranslation, multi-question selection, per-field wands
- Chat works best for: saved surveys, full translations, batch languages

**Testing:**

- Run `pytest posthog/api/test/test_survey.py::TestSurvey*Translation -v`
- Test on individual branches for focused feature testing
- Use PER-FIELD branch for complete feature experience
