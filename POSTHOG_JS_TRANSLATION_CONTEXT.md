# PostHog-JS: Survey Translations Implementation Context

> **For AI Assistant**: This document contains everything you need to know to implement survey translation rendering in the `posthog-js` SDK.

---

## 🎯 What We're Building

**Multi-language survey support** - Allow surveys to be displayed in different languages based on the user's language preference.

### The Problem

Teams running global products need to collect feedback from users who speak different languages. Currently, surveys only support one language per survey, forcing teams to either:

- **Create duplicate surveys** for each language → maintenance nightmare, fragmented analytics
- **Use English-only surveys** → tanks response rates from non-English speakers

### The Solution

One survey, multiple languages. Customers add translations in PostHog UI, and end users automatically see their language version.

---

## 📍 Where We Are Now

### ✅ DONE: Backend Support (PR #45096)

- **Repository**: `PostHog/posthog` (main backend repo)
- **Branch**: `feat/survey-i18n-backend-foundation`
- **Status**: Implemented and merged

**What it does:**

- Stores translations in database (`Survey.translations` and `Question.translations`)
- Validates translation structure (choices arrays must match, XSS prevention, etc.)
- Sanitizes HTML with nh3
- API endpoints accept and return translations

**Data structure:**

```python
# Survey model
{
    "translations": {
        "fr": {
            "name": "Enquête de satisfaction",
            "description": "Aidez-nous à améliorer",
            "thankYouMessageHeader": "Merci!",
            "thankYouMessageDescription": "Nous examinerons vos réponses",
            "thankYouMessageCloseButtonText": "Fermer"
        },
        "es": { ... }
    },
    "questions": [
        {
            "type": "rating",
            "question": "How satisfied are you?",
            "translations": {
                "fr": {
                    "question": "Dans quelle mesure êtes-vous satisfait?",
                    "description": "...",
                    "buttonText": "Envoyer",
                    "lowerBoundLabel": "Pas satisfait",
                    "upperBoundLabel": "Très satisfait"
                }
            }
        },
        {
            "type": "multiple_choice",
            "question": "Which features do you use?",
            "choices": ["Analytics", "Replay", "Flags"],
            "translations": {
                "fr": {
                    "question": "Quelles fonctionnalités utilisez-vous?",
                    "choices": ["Analytique", "Relecture", "Indicateurs"]
                }
            }
        }
    ]
}
```

### ✅ DONE: Frontend UI (PR #45281)

- **Repository**: `PostHog/posthog` (same repo, frontend code)
- **Branch**: `feat/surveys-translations-frontend`
- **Status**: Implemented

**What it does:**

- "Translations" tab in survey editor
- Language management (add/remove languages)
- Translation editing mode with validation
- Choice synchronization (add/remove choices = update all translations)
- Pre-save validation (empty strings, XSS prevention, etc.)

### ❌ TODO: posthog-js SDK Rendering

**Repository**: `PostHog/posthog-js` (separate repository)
**What's missing**: The SDK doesn't know how to render translated surveys yet!

**Current behavior**: SDK fetches survey from API, but always displays default language fields - ignores `translations` object entirely.

**Required behavior**: SDK should detect user's language and merge translated fields before rendering.

---

## 🎯 What Needs to Be Built (Your Task)

### High-Level Requirements

1. **Detect user's language** from person properties
2. **Fetch survey with translations** (already returned by API)
3. **Merge translated fields** with default fields
4. **Render the translated version** to the user
5. **Track which language was shown** (for analytics)

### Detailed Specification

#### 1. Language Detection

Language detection is strictly based on the specified person language property

**Important considerations:**

- Normalize language codes (case-insensitive, handle variants)
- Support both exact matches (`fr-CA`) and fallback to base language (`fr`)
- Case-insensitive matching (`FR` = `fr`)
- If translation doesn't exist for detected language, use default

#### 2. Translation Merging Logic

**Core principle**: Merge translated fields **on top of** default fields.

```typescript
// Pseudo-code for translation merging
function mergeSurveyTranslations(survey, targetLanguage) {
  if (!survey.translations || !survey.translations[targetLanguage]) {
    return survey // No translation, use default
  }

  const translated = { ...survey }
  const translation = survey.translations[targetLanguage]

  // Merge survey-level fields
  if (translation.name) translated.name = translation.name
  if (translation.description) translated.description = translation.description

  // Merge appearance fields (thank you message)
  if (translated.appearance && translation.thankYouMessageHeader) {
    translated.appearance.thankYouMessageHeader = translation.thankYouMessageHeader
  }
  if (translated.appearance && translation.thankYouMessageDescription) {
    translated.appearance.thankYouMessageDescription = translation.thankYouMessageDescription
  }
  if (translated.appearance && translation.thankYouMessageCloseButtonText) {
    translated.appearance.thankYouMessageCloseButtonText = translation.thankYouMessageCloseButtonText
  }

  // Merge question-level fields
  translated.questions = survey.questions.map((question) => {
    const questionTranslation = question.translations?.[targetLanguage]
    if (!questionTranslation) return question

    const translatedQuestion = { ...question }

    // Text fields
    if (questionTranslation.question) translatedQuestion.question = questionTranslation.question
    if (questionTranslation.description) translatedQuestion.description = questionTranslation.description
    if (questionTranslation.buttonText) translatedQuestion.buttonText = questionTranslation.buttonText
    if (questionTranslation.link) translatedQuestion.link = questionTranslation.link

    // Rating question fields
    if (questionTranslation.lowerBoundLabel) translatedQuestion.lowerBoundLabel = questionTranslation.lowerBoundLabel
    if (questionTranslation.upperBoundLabel) translatedQuestion.upperBoundLabel = questionTranslation.upperBoundLabel

    // Multiple choice fields
    if (questionTranslation.choices && Array.isArray(questionTranslation.choices)) {
      translatedQuestion.choices = questionTranslation.choices
    }

    return translatedQuestion
  })

  return translated
}
```

#### 3. Tracking Language Shown

**Critical for analytics**: We need to know which language each user saw.

```javascript
// When capturing survey response
posthog.capture('survey sent', {
  $survey_id: survey.id,
  $survey_response: answers,
  $survey_language: actualLanguageShown, // NEW FIELD - track this!
  // ... other properties
})
```

**Why this matters:**

- Enables filtering responses by language in results page
- Allows A/B testing different translations
- Helps measure completion rates per language

#### 4. API Changes (if needed)

**Good news**: API already returns translations! No backend changes needed.

The `/api/surveys/` endpoint already includes the full `translations` object in the response.

#### 5. Configuration

Allow developers to specify user's language with person language property:

```javascript
posthog.identify('user123', {
  language: 'fr-CA', // Canadian French
})
```

_Language codes are basically any string - allows customers to use their own language keys (e.g., "es", "es-MX", "english", "french")_

## 📋 Implementation Checklist

### Phase 1: Core Translation Rendering

- [ ] Add language detection utility function
  - [ ] Check person properties for `language` field
  - [ ] Handle language variants (en-US → en)
  - [ ] Case-insensitive matching
- [ ] Implement translation merging logic
  - [ ] Merge survey-level fields (name, description)
  - [ ] Merge thank you message fields
  - [ ] Merge question text fields
  - [ ] Merge choices arrays for MCQ/single-choice
  - [ ] Merge rating labels (lowerBound/upperBound)
  - [ ] Merge link URLs
- [ ] Update survey rendering to use merged translations
- [ ] Track `$survey_language` in response events

### Phase 2: Testing & Edge Cases

- [ ] Test with missing translations (fallback to default)
- [ ] Test with partial translations (some fields translated, some not)
- [ ] Test with invalid language codes
- [ ] Test language variant fallback (fr-CA → fr → en)
- [ ] Test with empty translation objects
- [ ] Verify choices array integrity (same length as default)

### Phase 3: Configuration & API

- [ ] Add `language` option to survey config
- [ ] Add global `survey_language` config option
- [ ] Update TypeScript types for translation structure
- [ ] Update documentation

### Phase 4: Analytics Enhancement (Future)

- [ ] Ensure `$survey_language` is captured consistently
- [ ] Consider adding language to survey impression events
- [ ] Document analytics schema changes

---

## 🗂️ File Structure in posthog-js

**Key files to modify:**

```text
posthog-js/
├── src/
│   ├── posthog-surveys.ts          # Main survey logic - ADD translation merging here
│   ├── posthog-surveys-types.ts    # Type definitions - ADD translation types
│   ├── utils.ts                     # Utilities - ADD language detection
│   └── posthog-core.ts             # Core - might need config additions
└── testcafe/                        # Tests
    └── surveys.spec.ts              # ADD translation tests
```

**Where to implement:**

1. **Language detection**: `src/utils.ts` or new `src/survey-translations.ts`
2. **Translation merging**: `src/posthog-surveys.ts` - in the survey fetching/rendering logic
3. **Type definitions**: `src/posthog-surveys-types.ts` - add translation interfaces
4. **Event capture**: Update wherever survey responses are captured to include `$survey_language`

_NOTE: This structure suggests what and where to modify, DO NOT treat as rule book, IT MIGHT BE WRONG AND INCOMPLETE! So it's up to you verify wheret to make your chagnes and what changes to make!_

## 🔍 Important Details from Backend Implementation

### Translation Field Mapping

**Survey-level translations:**

- `translations[lang].name` → `survey.name`
- `translations[lang].description` → `survey.description`
- `translations[lang].thankYouMessageHeader` → `survey.appearance.thankYouMessageHeader`
- `translations[lang].thankYouMessageDescription` → `survey.appearance.thankYouMessageDescription`
- `translations[lang].thankYouMessageCloseButtonText` → `survey.appearance.thankYouMessageCloseButtonText`

**Question-level translations:**

- `question.translations[lang].question` → `question.question`
- `question.translations[lang].description` → `question.description`
- `question.translations[lang].buttonText` → `question.buttonText`
- `question.translations[lang].link` → `question.link` (for link questions)
- `question.translations[lang].choices[]` → `question.choices[]` (for MCQ/single-choice)
- `question.translations[lang].lowerBoundLabel` → `question.lowerBoundLabel` (for rating)
- `question.translations[lang].upperBoundLabel` → `question.upperBoundLabel` (for rating)

### Validation Rules (already enforced by backend)

✅ **Choices arrays must match length**: `translated_choices.length === original_choices.length`
✅ **XSS prevention**: All text sanitized, link URLs must be `https://` or `mailto:`
✅ **Empty strings not allowed**: All fields must have content if present
✅ **Type safety**: Choices must be array, other fields must be strings

**Your SDK implementation doesn't need to validate these** - backend already does. Just merge and render!

---

## 🧪 Testing Strategy

### Manual Testing Checklist

1. **Basic translation rendering**
   - Create survey with French translation
   - Set person property `language: 'fr'`
   - Verify French text displays

2. **Language fallback**
   - Set person property `language: 'fr-CA'`
   - Survey only has `fr` translation
   - Verify falls back to `fr` (not default)

3. **Missing translation**
   - Set person property `language: 'de'`
   - Survey has no German translation
   - Verify shows default (English)

4. **Partial translation**
   - Survey has French translation for name only
   - Other fields missing
   - Verify name shows French, others show default

5. **Choice questions**
   - Multiple choice with French translation
   - Verify choices display in French
   - Verify array length matches

6. **Analytics tracking**
   - Submit survey response
   - Verify `$survey_language` is captured
   - Check event in PostHog

### Automated Tests

Add to `testcafe/surveys.spec.ts`:

```typescript
test('Survey displays in user language from person properties', async (t) => {
  // Set person property
  await posthog.identify('test-user', { language: 'fr' })

  // Trigger survey with French translation
  await posthog.loadSurvey('test-survey-id')

  // Verify French text displays
  await t.expect(Selector('.survey-question').innerText).contains('Que pensez-vous')
})

test('Survey falls back to default when translation missing', async (t) => {
  await posthog.identify('test-user', { language: 'de' })
  await posthog.loadSurvey('test-survey-id')

  // Verify English (default) displays
  await t.expect(Selector('.survey-question').innerText).contains('What do you think')
})

test('Survey tracks language shown in analytics', async (t) => {
  await posthog.identify('test-user', { language: 'fr' })
  await posthog.loadSurvey('test-survey-id')
  await submitSurveyResponse()

  // Verify $survey_language captured
  const events = await getEventBuffer()
  await t.expect(events.find((e) => e.event === 'survey sent').$survey_language).eql('fr')
})
```

---

## 🚨 Edge Cases to Handle

1. **Language code variants**: `en-US`, `en-GB`, `en-us`, `EN-US`
   - Solution: Normalize to lowercase, try exact match first, then base language

2. **Empty translation objects**: `translations: { fr: {} }`
   - Solution: Treat as missing translation, use default

3. **Null/undefined values**: `translations.fr.question = null`
   - Solution: Skip null/undefined, keep default value

4. **Array length mismatches**: Backend prevents this, but SDK should handle gracefully
   - Solution: If mismatch detected, log warning and use default

---

## 💡 Implementation Tips

### Recommended Approach

1. **Start simple**: Get basic language detection + merging working first
2. **Test incrementally**: Test each field type (text, choices, ratings) separately
3. **Handle fallbacks carefully**: Language variant fallback is tricky, test thoroughly
4. **Add logging**: Console.log language detection and merging for debugging
5. **Update types**: Keep TypeScript types in sync with implementation

### Common Pitfalls to Avoid

❌ **Don't mutate original survey object** - always create copies
❌ **Don't assume translations exist** - always check for undefined
❌ **Don't forget to track language** - analytics is critical for this feature
❌ **Don't break existing surveys** - must be backward compatible
❌ **Don't hardcode language codes** - support any language code

### Performance Considerations

- Language detection happens once per survey load (minimal overhead)
- Translation merging is synchronous and fast (just object spreading)
- No additional API calls needed (translations already in survey payload)
- Consider memoizing merged survey to avoid re-merging on re-renders

---

## 🔗 External Links

- **Issue**: https://github.com/PostHog/posthog/issues/42154
- **Backend PR**: https://github.com/PostHog/posthog/pull/45096
- **Frontend PR**: https://github.com/PostHog/posthog/pull/45281
- **posthog-js repo**: https://github.com/PostHog/posthog-js
- **Docs (to be updated)**: https://posthog.com/docs/surveys

---

## 🎬 Next Steps

1. **Review this document** to understand the full context
2. **Review the frontend PR body** (attached) to see UI implementation
3. **Clone posthog-js** repository
4. **Find the survey rendering code** (likely `src/posthog-surveys.ts`)
5. **Implement language detection + merging** as specified above
6. **Add tests** to verify translation rendering
7. **Update TypeScript types** to include translation structure
8. **Submit PR** with description referencing this context doc

---

## 📝 Questions to Consider

Before starting implementation, think about:

1. **Where should language detection happen?**
   - In survey fetch? In render? Both?

2. **Should we cache the merged survey?**
   - Avoid re-merging on every render

3. **How to handle language changes mid-session?**
   - If user language changes, should survey re-render?

4. **Should we expose the language to external code?**
   - For debugging or customization

5. **What about survey impressions?**
   - Should `survey shown` events also include language?

---

## ✅ Success Criteria

Your implementation is complete when:

- [ ] User with `language: 'fr'` person property sees French survey
- [ ] User with no language property sees default survey
- [ ] Language variants fall back correctly (`fr-CA` → `fr` → default)
- [ ] All translatable fields are merged (name, description, questions, choices, thank you message)
- [ ] `$survey_language` is tracked in survey response events
- [ ] Tests cover all edge cases
- [ ] TypeScript types are updated
- [ ] No regression on existing surveys (backward compatible)
- [ ] Works with all question types (rating, MCQ, single-choice, open, link)

---

## 🙌 You've Got This!

This is the final piece to complete the surveys translation epic. The hard parts (backend storage, frontend UI, validation) are already done. You just need to:

1. Detect language
2. Merge fields
3. Track what was shown

Keep it simple, test thoroughly, and ship it! 🚀
