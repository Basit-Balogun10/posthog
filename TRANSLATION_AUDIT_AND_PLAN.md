# Survey Translations: Comprehensive Audit & Implementation Plan

## Executive Summary

This document outlines critical issues found during auditing the survey translation feature, along with implementation plans for fixes and enhancements.

---

## 🚨 Critical Issues Found

### 1. **Translation Deletion Does Not Clean Up Question-Level Translations**

**Current Behavior:**

- `removeLanguage()` in [SurveyTranslations.tsx](frontend/src/scenes/surveys/SurveyTranslations.tsx#L82-L88) only deletes `survey.translations[lang]`
- Question-level translations stored in `questions[].translations[lang]` are NOT cleaned up
- This leaves orphaned translation data in the database

**Impact:**

- Database bloat with unused translation data
- Potential confusion if language is re-added later (old translations might reappear)
- Data integrity issue

**Fix Required:**

```typescript
const removeLanguage = (lang: string): void => {
  // Remove survey-level translations
  const currentTranslations = { ...survey.translations }
  delete currentTranslations[lang]
  setSurveyValue('translations', currentTranslations)

  // MISSING: Remove question-level translations
  const updatedQuestions = survey.questions.map((question) => {
    if (question.translations && question.translations[lang]) {
      const questionTranslations = { ...question.translations }
      delete questionTranslations[lang]
      return {
        ...question,
        translations: questionTranslations,
      }
    }
    return question
  })
  setSurveyValue('questions', updatedQuestions)

  if (editingLanguage === lang) {
    setEditingLanguage(null)
  }
}
```

---

### 2. **Question Type Changes Don't Clean Up Translations**

**Current Behavior:**

- When changing question type (e.g., Multiple Choice → Open Text), the default question fields are reset
- However, `question.translations[lang]` for ALL languages still contain the old question type's fields
- Example: Changing MCQ to Open Text leaves `translations[lang].choices` orphaned in all languages

**Code Location:**

- [SurveyEditQuestionRow.tsx](frontend/src/scenes/surveys/SurveyEditQuestionRow.tsx#L234-L260) handles type changes
- `setDefaultForQuestionType()` in surveyLogic resets default fields but ignores translations

**Impact:**

- Invalid translation data persists (e.g., choices for non-MCQ questions)
- Backend validation might reject the survey on save if structure is incompatible
- Inconsistent data model

**Fix Required:**
When question type changes, clean up translations:

```typescript
// In surveyLogic.tsx, enhance setDefaultForQuestionType
const cleanedTranslations = question.translations
  ? Object.entries(question.translations).reduce((acc, [lang, trans]) => {
      const cleanedTrans = { ...trans }

      // Remove fields that don't apply to new type
      if (newType !== SurveyQuestionType.SingleChoice && newType !== SurveyQuestionType.MultipleChoice) {
        delete cleanedTrans.choices
      }
      if (newType !== SurveyQuestionType.Link) {
        delete cleanedTrans.link
      }
      if (newType !== SurveyQuestionType.Rating) {
        delete cleanedTrans.lowerBoundLabel
        delete cleanedTrans.upperBoundLabel
      }

      acc[lang] = cleanedTrans
      return acc
    }, {})
  : undefined

newQuestion.translations = cleanedTranslations
```

---

### 3. **Adding/Removing Choices Doesn't Update Translations**

**Current Behavior:**

- Users can add/remove choices in default language
- Translation choices arrays are NOT updated to match the new length
- Backend validation requires: `len(translated_choices) === len(original_choices)`

**Code Location:**

- [SurveyEditQuestionRow.tsx](frontend/src/scenes/surveys/SurveyEditQuestionRow.tsx#L480-L530) - Add/remove choice buttons

**Impact:**

- Backend will reject save with error: "Translation has X choices but question has Y choices"
- Users will be confused why their survey won't save
- Breaking change requires users to manually update every language

**Backend Validation:**

```python
# posthog/api/survey.py lines 560-572
if len(translated_choices) != len(original_choices):
    raise serializers.ValidationError(
        f"Question {index + 1}: Translation '{lang_code}' has {len(translated_choices)} choices "
        f"but question has {len(original_choices)} choices. Array lengths must match."
    )
```

**Fix Required:**

Option A: **Automatic Synchronization (Recommended)**

- When adding choice to default: Add empty string to all translation choices arrays at same index
- When removing choice from default: Remove from all translation choices arrays at same index
- When reordering choices: Reorder in all translations

Option B: **Clear Translated Choices on Change**

- When choices change in default language, clear all `translations[lang].choices`
- Show warning: "Modifying choices will clear translated choices in all languages"
- Simpler but requires re-translation

---

### 4. **Translations Missing from Survey-Level Validation**

**Current Behavior:**

- `validate_translations()` validates name, description, thankYouMessage fields
- But it's a separate method from `validate_questions()`
- No cross-validation between survey-level and question-level translations

**Backend Code:**

- [survey.py](posthog/api/survey.py#L383-L423) - `validate_translations()`
- [survey.py](posthog/api/survey.py#L473-L576) - `validate_questions()` with inline translations

**Potential Issue:**

- Survey could have language 'fr' in `survey.translations` but no 'fr' in any `question.translations`
- Or vice versa - inconsistent translation coverage

**Enhancement Needed:**

- Add validation to ensure consistent language codes across survey-level and question-level translations
- Or at minimum, document that partial translations are allowed

---

## 📊 Results Page Analysis

### Current State

**What Results Page Shows:**

- [SurveyView.tsx](frontend/src/scenes/surveys/SurveyView.tsx#L350-L363) - `SurveyResponsesByQuestionV2`
- Displays question visualizations for each question
- Shows question text from `question.question` (default language only)
- Does NOT display any translation metadata

**Response Data Structure:**
Responses are stored with:

- User's answers (in whatever language they saw)
- No indication of which language the survey was displayed in
- No tracking of which translation was shown

### Issues Identified

1. **No Language Tracking in Responses**
   - We don't know which language version of the survey each user saw
   - Can't filter/segment responses by language
   - Can't compare completion rates across languages

2. **Question Labels Always in Default Language**
   - Results page shows `question.question` only
   - If user saw French version, results still show English question text
   - Confusing for teams managing multilingual surveys

3. **No Way to Filter by Language**
   - [SurveyResponseFilters.tsx](frontend/src/scenes/surveys/SurveyResponseFilters.tsx) - Current filters don't include language
   - Can't analyze "How did French speakers respond vs English speakers?"

### Enhancement Opportunities

#### Phase 1: Add Language Tracking (Backend)

**Store language in response:**

```typescript
// In survey-web.ts (frontend SDK that sends responses)
posthog.capture('survey sent', {
    $survey_id: survey.id,
    $survey_response: answers,
    $survey_language: currentLanguage, // NEW FIELD
    ...
})
```

**Backend changes:**

- Add `language` field to event properties
- Index by language for faster querying

#### Phase 2: Results Page Language Segmentation (Frontend)

**Add language filter:**

- New dropdown in `SurveyResponseFilters`: "Filter by language"
- Options: "All languages" + list of languages from `survey.translations`
- Filter queries to only show responses where `$survey_language` matches

**Show translated question text:**

- If filtering by specific language, show question text in that language
- Fallback to default if translation doesn't exist

#### Phase 3: Language-Specific Analytics

**New metrics to display:**

```text
Language Performance Dashboard:
┌─────────────────────────────────────────┐
│ Responses by Language                    │
│ • English: 450 (45%)                     │
│ • Spanish: 320 (32%)                     │
│ • French: 230 (23%)                      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Completion Rate by Language              │
│ • English: 78%                           │
│ • Spanish: 82% ↑                         │
│ • French: 71%                            │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Average Rating by Language (NPS)         │
│ • English: 7.8                           │
│ • Spanish: 8.2 ↑                         │
│ • French: 7.3                            │
└─────────────────────────────────────────┘
```

**Implementation:**

- New component: `SurveyLanguageBreakdown.tsx`
- Query responses grouped by `$survey_language`
- Calculate metrics per language
- Display in new tab or section on results page

---

## 🔍 Backend Validation Audit

### Current Validations

#### Survey-Level Translations (`validate_translations`)

✅ Validates structure (must be dict)
✅ Validates field types (strings)
✅ HTML sanitization with nh3
✅ Fields: name, description, thankYouMessageHeader, thankYouMessageDescription, thankYouMessageCloseButtonText

#### Question-Level Translations (`_validate_question_translations`)

✅ Validates structure (must be dict of dicts)
✅ Validates field types (strings for text, list for choices)
✅ HTML sanitization with nh3
✅ Link validation (URL schemes)
✅ **Choices array length validation** - must match original
✅ Fields: question, description, buttonText, link, lowerBoundLabel, upperBoundLabel, choices

### Frontend Handling Analysis

#### ✅ **Well-Handled Validations:**

1. **Disabled Fields During Translation**
   - Question type, display type, optional flag all disabled when `editingLanguage` active
   - Matches backend constraint that these are default-language only

2. **Choices Matching**
   - Frontend initializes choices arrays in `addLanguage()`
   - Displays all choices with placeholders showing default text
   - Uses `name={getFieldName('choices')}` to save to correct location

3. **HTML Sanitization**
   - Backend sanitizes with nh3, frontend sends raw
   - This is correct - sanitize on write, not read

#### ⚠️ **Potential Mismatches:**

1. **No Frontend Validation for Choices Length**
   - Backend rejects if `len(translated_choices) !== len(original_choices)`
   - Frontend allows editing choices array but doesn't validate length before save
   - **Result:** User finds out on save, not while editing

2. **No Warning When Changing Choices**
   - User can add/remove choices in default language while translations exist
   - No warning that this will break translated choices
   - **Result:** Confusing backend error on save

3. **Link URL Validation**
   - Backend validates URL schemes (https/mailto only)
   - Frontend LemonInput doesn't validate until save
   - **Result:** User finds out on save

4. **Missing Translation Cleanup on Type Change**
   - Backend will accept invalid fields in translations (won't error)
   - But frontend should clean them up for data hygiene
   - **Result:** Database bloat, potential confusion

### Recommendations for Frontend Improvements

#### 1. Add Pre-Save Validation

```typescript
// In surveyLogic.tsx, before updateSurvey()
const validateTranslationsBeforeSave = (survey: Survey): string[] => {
  const errors: string[] = []

  // Check choices array lengths
  survey.questions.forEach((question, index) => {
    if (!question.translations) return

    const originalChoices = question.choices || []
    Object.entries(question.translations).forEach(([lang, trans]) => {
      if (trans.choices && trans.choices.length !== originalChoices.length) {
        errors.push(
          `Question ${index + 1}: ${lang} translation has ${trans.choices.length} choices but default has ${originalChoices.length}`
        )
      }
    })
  })

  // Check link URL schemes
  survey.questions.forEach((question, index) => {
    if (question.link && !question.link.match(/^(https:|mailto:)/)) {
      errors.push(`Question ${index + 1}: Link must start with https:// or mailto:`)
    }
    if (question.translations) {
      Object.entries(question.translations).forEach(([lang, trans]) => {
        if (trans.link && !trans.link.match(/^(https:|mailto:)/)) {
          errors.push(`Question ${index + 1}: ${lang} translation link must start with https:// or mailto:`)
        }
      })
    }
  })

  return errors
}

// Before save:
const errors = validateTranslationsBeforeSave(survey)
if (errors.length > 0) {
  lemonToast.error(`Cannot save: ${errors.join('; ')}`)
  return
}
```

#### 2. Add Warnings for Destructive Actions

```typescript
// When adding/removing choices with translations present
const hasTranslations = survey.questions.some((q) => q.translations && Object.keys(q.translations).length > 0)

if (hasTranslations) {
  LemonDialog.open({
    title: 'Modify choices?',
    description:
      'This survey has translations. Modifying choices will clear translated choices in all languages. Continue?',
    primaryButton: {
      children: 'Continue',
      status: 'danger',
      onClick: () => proceedWithChange(),
    },
  })
}
```

---

## 📋 Implementation Priority

### P0 - Critical (Must Fix Before Release)

1. ✅ Translation deletion cleanup (question-level)
2. ✅ Question type change cleanup (translations)
3. ✅ Choices add/remove synchronization
4. Pre-save validation for choices length

### P1 - High (Should Fix Before Release)

1. Link URL validation feedback
2. Warning dialogs for destructive actions
3. Frontend validation messages matching backend errors

### P2 - Medium (Can Be Follow-Up)

1. Language tracking in responses (backend)
2. Language filter on results page
3. Translated question text in results

### P3 - Low (Future Enhancement)

1. Language-specific analytics dashboard
2. Completion rate comparison by language
3. A/B testing different translations

---

## 🧪 Testing Checklist

### Translation Deletion

- [ ] Delete language → verify `questions[].translations[lang]` removed
- [ ] Delete language while editing it → verify switches to default
- [ ] Re-add deleted language → verify clean slate (no old data)

### Question Type Changes

- [ ] MCQ → Open Text → verify choices removed from all translations
- [ ] Rating → MCQ → verify rating fields (lowerBoundLabel) removed
- [ ] Link → Rating → verify link field removed

### Choices Synchronization

- [ ] Add choice in default → verify empty string added to all translation choices
- [ ] Remove choice in default → verify removed from all translation choices at same index
- [ ] Reorder choices → verify same reorder in all translations
- [ ] With hasOpenChoice: add/remove → verify "Other" handled correctly

### Backend Validation

- [ ] Save with mismatched choices length → verify clear error message
- [ ] Save with invalid link URL → verify error caught
- [ ] Save with XSS in translation → verify sanitized
- [ ] Save with missing required question → verify error

### Results Page

- [ ] Display results with translations present → verify shows default language
- [ ] Filter by specific answer → verify works regardless of translation
- [ ] Export results → verify includes all responses

---

## 💭 Open Questions for Discussion

1. **Choices Synchronization Strategy:**
   - Auto-sync (P0) vs Clear on change (simpler)?
   - Should we allow different numbers of choices per language? (Backend says no)

2. **Language in Responses:**
   - Should we track language even if not filtering by it?
   - How to handle language detection (URL param, browser, explicit user selection)?

3. **Results Page Enhancements:**
   - Should translated question text be shown based on selected filter language?
   - How much language-specific analytics is needed in v1?

4. **Partial Translations:**
   - Should we require all questions translated if survey-level is translated?
   - Or allow partial translations (some questions in some languages)?

---

## 📝 Next Steps

1. Review this document with team
2. Prioritize issues (P0 must be fixed now)
3. Implement critical fixes (translation cleanup)
4. Add frontend validation before save
5. Test thoroughly with all edge cases
6. Plan results page enhancements (separate PR)
