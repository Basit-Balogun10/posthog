## 🌍 Multi-Language Surveys - Complete Demo Guide

> **Scenario:** You're a SaaS company with users in France, Mexico, and the US. You want to collect product feedback in their native languages.

---

## Step 1: Create the Base Survey (Default Language)

Navigate to **Surveys** → Click **"New Survey"** → Select **"Product feedback"** template

Fill in the default English content:

```text
Survey Name: Product Satisfaction Q1 2026
Description: Help us improve our product

Question 1 (Rating):
- Question: "How satisfied are you with our product?"
- Lower Label: "Not satisfied"
- Upper Label: "Very satisfied"

Question 2 (Multiple Choice):
- Question: "Which features do you use most?"
- Choices:
  • Analytics Dashboard
  • Session Replay
  • Feature Flags
  • A/B Testing
  • Surveys

Question 3 (Open):
- Question: "What could we improve?"
- Description: "Your feedback helps us prioritize our roadmap"
- Button Text: "Submit Feedback"

Thank You Message:
- Header: "Thank you for your feedback!"
- Description: "We'll review your responses and use them to improve our product."
- Close Button Text: "Close"
```

---

## Step 2: Add French Translation

1. Click the **"Translations"** tab at the top
2. In the language dropdown, type **"French"** or **"fr"** and select it
3. The language will appear in the list below - click on **"French (fr)"** to start editing

**You'll see:**

- Yellow banner appears: "Editing translation for French. Only user-facing text can be translated..."
- Language switcher shows: `Default (Original)` | `French (fr)`
- All translatable fields now show the default English text as placeholders

Translate all the content:

```text
Survey Name: Satisfaction produit Q1 2026
Description: Aidez-nous à améliorer notre produit

Question 1 (Rating):
- Question: "Dans quelle mesure êtes-vous satisfait de notre produit ?"
- Lower Label: "Pas satisfait"
- Upper Label: "Très satisfait"

Question 2 (Multiple Choice):
- Question: "Quelles fonctionnalités utilisez-vous le plus ?"
- Choices:
  • Tableau de bord analytique
  • Relecture de session
  • Indicateurs de fonctionnalités
  • Tests A/B
  • Enquêtes

Question 3 (Open):
- Question: "Que pourrions-nous améliorer ?"
- Description: "Vos commentaires nous aident à prioriser notre feuille de route"
- Button Text: "Envoyer les commentaires"

Thank You Message:
- Header: "Merci pour vos commentaires !"
- Description: "Nous examinerons vos réponses et les utiliserons pour améliorer notre produit."
- Close Button Text: "Fermer"
```

**Key things to notice:**

- Choices automatically show default text as placeholders
- You cannot edit question types, targeting, or scheduling (non-translatable fields)
- If you had added/removed choices in default, they would auto-sync here

---

## Step 3: Add Spanish Translation

Still in the **"Translations"** tab:

1. In the language dropdown, type **"es-MX"** (Mexican Spanish)
2. Click on **"Spanish - Mexico (es-MX)"** to start editing

**Note:** You can use any language code - not limited to the preset list. Regional variants like es-MX vs es-ES, fr-FR vs fr-CA all work.

Translate the content:

```text
Survey Name: Satisfacción del producto Q1 2026
Description: Ayúdanos a mejorar nuestro producto

Question 1 (Rating):
- Question: "¿Qué tan satisfecho estás con nuestro producto?"
- Lower Label: "No satisfecho"
- Upper Label: "Muy satisfecho"

Question 2 (Multiple Choice):
- Question: "¿Cuáles funciones usas más?"
- Choices:
  • Panel de análisis
  • Repetición de sesión
  • Banderas de funciones
  • Pruebas A/B
  • Encuestas

Question 3 (Open):
- Question: "¿Qué podríamos mejorar?"
- Description: "Tus comentarios nos ayudan a priorizar nuestro plan"
- Button Text: "Enviar comentarios"

Thank You Message:
- Header: "¡Gracias por tus comentarios!"
- Description: "Revisaremos tus respuestas y las usaremos para mejorar nuestro producto."
- Close Button Text: "Cerrar"
```

---

## Step 4: Demo All Validation Features

### 4.1 Empty String Validation

**Demo empty default fields:**

1. Click on **"Default (Original)"**
2. Clear Question 1's question text (leave it empty)
3. Try to save

**See:** Validation error on default language: "Survey - Question 1 - Question text: Cannot be empty"

**Fill it back in and save successfully.**

---

### 4.2 Translation Placeholder Validation

**Demo `[Translation needed]` detection:**

1. Click on **"French (fr)"**
2. Leave Question 2's first choice as `[Translation needed]`
3. Try to save

**See:** Validation error: "French - Question 2 - Choice 1: Contains placeholder '[Translation needed]'"

**Validation banner shows:**

- Yellow collapsible banner at the top (sticky while scrolling)
- Errors grouped by language
- Click "French" to jump to that language
- Save button disabled with tooltip

---

### 4.3 Link URL Security Validation

**Demo XSS prevention:**

1. Add a new Link question in default language
2. In the Link URL field, try: `javascript:alert('xss')`
3. Try to save

**See:** Validation error: "Question 4 - Link URL: Must start with https:// or mailto:"

**Valid examples:**

- `https://example.com`
- `mailto:feedback@example.com`

This prevents XSS attacks via `javascript:`, `data:`, and other sketchy URI schemes.

---

### 4.4 Choice Synchronization

**Demo auto-sync when adding choices:**

1. Click on **"Default (Original)"**
2. Navigate to Question 2 (Multiple Choice)
3. Click "Add choice" button
4. Type: "Data Warehouse"
5. Switch to **"French (fr)"**

**See:** The new choice automatically appears with `[Translation needed]` placeholder at the same index

**Demo auto-sync when removing choices:**

1. Click on **"Default (Original)"**
2. Remove the last choice you just added
3. Switch to **"French (fr)"**

**See:** The choice is removed from French too - arrays stay in sync automatically

This prevents backend errors from mismatched choice array lengths.

---

### 4.5 Reverse Validation (Empty Default with Translation)

**Demo translating empty defaults:**

1. Click on **"Default (Original)"**
2. Add a new question (Question 4 - Open text)
3. Leave the question text empty in default
4. Click on **"French (fr)"**
5. Fill in the French translation: "Quelles sont vos attentes pour l'année prochaine ?"
6. Try to save

**See:** Validation error on **Default language**: "Question 4 - Question text: Cannot be empty (has translation)"

**Why this matters:**

- You cannot translate content that doesn't exist in the source
- Default language is the source of truth - must be complete first
- Error appears on default (not translation) to guide you to fix the root cause

---

### 4.6 Banner Priority System

**Demo validation banner takes priority:**

1. Have validation errors present (e.g., empty field)
2. Click on **"Spanish (es-MX)"**

**See:** Validation banner shows (yellow, sticky) - language editing banner is hidden

**Demo language banner returns when errors fixed:**

1. Fix all validation errors
2. Still in translation mode

**See:** Yellow "Editing translation for Spanish" banner now shows

Only one banner at a time - validation (critical) takes priority over language context.

---

### 4.7 Empty Choice in Default Language

**Demo empty choice detection:**

1. Click on **"Default (Original)"**
2. Add a new choice to Question 2, but leave it empty (just blank)
3. Try to save

**See:** Validation error: "Default - Question 2 - Choice 6: Cannot be empty"

This ensures default language is always complete, even with translations present.

---

## Step 5: Demo UX Polish Features

### 5.1 Smart Field Restrictions

**When in translation mode:**

1. Click on **"French (fr)"**
2. Try to change Question 1's type (Rating → Multiple Choice)

**See:** Question type dropdown is disabled/view-only

**Other restricted fields:**

- Question types
- Display types (for rating questions)
- Optional checkbox
- Adding/removing questions

**Why?** Prevents structural changes that would break translation compatibility. All structure changes must be in default language.

---

### 5.2 Language Switcher Clarity

**Demo the switcher:**

1. Look at the language list in Translations tab
2. Notice the highlighted language shows which you're editing
3. "Default (Original)" clearly indicates the source language

**Quick navigation:**

- Click any language to instantly switch
- Validation errors let you click language names to jump directly
- Inline "default language" link in yellow banner for quick return

---

### 5.3 Intelligent Placeholder Behavior

**Demo placeholders:**

1. Add a new language (e.g., German - "de")
2. Notice all text fields show default text as greyed-out placeholders
3. Type to replace placeholder
4. Clear your text

**See:** Placeholder returns, showing default text for reference

**For choices:**

- Original choices show as placeholders
- New choices show `[Translation needed]`
- Prevents confusion about what to translate

---

### 5.4 Delete Language Confirmation

**Demo safe deletion:**

1. Try to delete French translation
2. Click the trash icon

**See:** Confirmation dialog: "Are you sure you want to delete translation for **French**? All translated content for this language will be permanently lost."

Prevents accidental deletion of translation work.

---

### 5.5 Sticky Banner Behavior

**Demo sticky positioning:**

1. Create a survey with many questions (5+)
2. Have validation errors present
3. Scroll down the page

**See:**

- Validation banner stays visible at top (sticky)
- Survey title/description scroll normally (not sticky)
- Can always see errors while scrolling to fix them

---

## Step 6: Additional Feature Demos

### 6.1 Regional Variant Support

**Demo custom language codes:**

1. Add "French - Canada" (`fr-CA`)
2. Add "Spanish - Spain" (`es-ES`)
3. Add "Chinese - Simplified" (`zh-CN`)

**See:** All regional variants work - not limited to preset list

---

### 6.2 Partial Translation Support

**Demo incomplete translations:**

1. In a translation, only fill in survey name and Question 1
2. Leave Question 2 and Question 3 empty (no text entered)
3. Save

**See:** Saves successfully - fields without translation will fall back to default when shown to users

---

### 6.3 Question Type Change Cleanup

**Demo translation cleanup:**

1. In default language, create a Multiple Choice question with translations
2. Change question type to Open Text
3. Switch to a translation language

**See:** The `choices` field is removed from translation (no longer applicable)

Translations automatically clean up incompatible fields when structure changes.
