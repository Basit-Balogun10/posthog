import { useActions, useValues } from 'kea'
import React from 'react'

import { IconMagicWand, IconTrash } from '@posthog/icons'
import { LemonButton, LemonCheckbox, LemonDialog, LemonInputSelect, LemonSelect } from '@posthog/lemon-ui'

import { SurveyQuestionType } from '~/types'

import { surveyLogic } from './surveyLogic'

export const COMMON_LANGUAGES = [
    { value: 'en', label: 'English (en)' },
    { value: 'en-US', label: 'English - US (en-US)' },
    { value: 'en-GB', label: 'English - UK (en-GB)' },
    { value: 'es', label: 'Spanish (es)' },
    { value: 'es-ES', label: 'Spanish - Spain (es-ES)' },
    { value: 'es-MX', label: 'Spanish - Mexico (es-MX)' },
    { value: 'fr', label: 'French (fr)' },
    { value: 'fr-FR', label: 'French - France (fr-FR)' },
    { value: 'fr-CA', label: 'French - Canada (fr-CA)' },
    { value: 'de', label: 'German (de)' },
    { value: 'de-DE', label: 'German - Germany (de-DE)' },
    { value: 'pt', label: 'Portuguese (pt)' },
    { value: 'pt-BR', label: 'Portuguese - Brazil (pt-BR)' },
    { value: 'pt-PT', label: 'Portuguese - Portugal (pt-PT)' },
    { value: 'zh', label: 'Chinese (zh)' },
    { value: 'zh-CN', label: 'Chinese - Simplified (zh-CN)' },
    { value: 'zh-TW', label: 'Chinese - Traditional (zh-TW)' },
    { value: 'ja', label: 'Japanese (ja)' },
    { value: 'ko', label: 'Korean (ko)' },
    { value: 'ru', label: 'Russian (ru)' },
    { value: 'ar', label: 'Arabic (ar)' },
    { value: 'hi', label: 'Hindi (hi)' },
    { value: 'it', label: 'Italian (it)' },
    { value: 'nl', label: 'Dutch (nl)' },
    { value: 'pl', label: 'Polish (pl)' },
    { value: 'tr', label: 'Turkish (tr)' },
]

export function SurveyTranslations(): JSX.Element {
    const { survey, editingLanguage, translatingLanguage } = useValues(surveyLogic)
    const {
        setSurveyValue,
        setEditingLanguage,
        autoTranslateSurvey,
        autoTranslateSurveyBatch,
        autoTranslateSurveyQuestion,
    } = useActions(surveyLogic)

    const [batchLanguages, setBatchLanguages] = React.useState<string[]>([])
    const [selectedQuestions, setSelectedQuestions] = React.useState<number[]>([])
    const [selectedLanguageForQuestions, setSelectedLanguageForQuestions] = React.useState<string | null>(null)

    const addedLanguages = Object.keys(survey.translations || {})

    const addLanguage = (lang: string): void => {
        if (!lang) {
            return
        }
        const currentTranslations = survey.translations || {}
        if (currentTranslations[lang]) {
            return
        }

        // Initialize each question's translation with choices arrays for multiple choice questions
        const updatedQuestions = survey.questions.map((question) => {
            if (
                question.type === SurveyQuestionType.SingleChoice ||
                question.type === SurveyQuestionType.MultipleChoice
            ) {
                return {
                    ...question,
                    translations: {
                        ...question.translations,
                        [lang]: {
                            ...question.translations?.[lang],
                            choices: question.choices || [],
                        },
                    },
                }
            }
            return question
        })

        setSurveyValue('questions', updatedQuestions)
        setSurveyValue('translations', {
            ...currentTranslations,
            [lang]: {
                name: survey.name || '',
                description: survey.description || '',
            },
        })
        setEditingLanguage(lang)
    }

    const removeLanguage = (lang: string): void => {
        // Remove survey-level translations
        const currentTranslations = { ...survey.translations }
        delete currentTranslations[lang]
        setSurveyValue('translations', currentTranslations)

        // Remove question-level translations
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

    return (
        <div className={`flex flex-col ${addedLanguages.length > 0 ? 'gap-4' : ''}`}>
            <div className="flex gap-2">
                <LemonInputSelect
                    mode="single"
                    options={COMMON_LANGUAGES.filter((l) => !addedLanguages.includes(l.value)).map((l) => ({
                        key: l.value,
                        label: l.label,
                    }))}
                    onChange={(values) => {
                        const lang = values[0]
                        if (lang) {
                            addLanguage(lang)
                        }
                    }}
                    placeholder="Add a language (e.g., 'fr', 'French', 'fr-CA')"
                    className="grow"
                    allowCustomValues
                    autoFocus={addedLanguages.length === 0}
                    value={[]}
                />
            </div>

            {addedLanguages.length > 0 && (
                <div className="border rounded p-3 space-y-3">
                    <h3 className="font-semibold text-sm">Batch translate</h3>
                    <div className="space-y-2">
                        <LemonInputSelect
                            mode="multiple"
                            options={COMMON_LANGUAGES.filter((l) => addedLanguages.includes(l.value)).map((l) => ({
                                key: l.value,
                                label: l.label,
                            }))}
                            onChange={(values) => setBatchLanguages(values)}
                            placeholder="Select languages to translate"
                            value={batchLanguages}
                        />

                        <LemonButton
                            icon={<IconMagicWand />}
                            type="primary"
                            fullWidth
                            onClick={(e) => {
                                if (batchLanguages.length > 0) {
                                    // Default: smart retranslation, Ctrl+click: full retranslation
                                    const onlyChangedFields = !(e.ctrlKey || e.metaKey)
                                    autoTranslateSurveyBatch(batchLanguages, onlyChangedFields)
                                }
                            }}
                            loading={translatingLanguage === 'batch'}
                            disabled={batchLanguages.length === 0 || !survey.id}
                            disabledReason={
                                !survey.id
                                    ? 'Save the survey first before translating'
                                    : batchLanguages.length === 0
                                      ? 'Select at least one language'
                                      : undefined
                            }
                        >
                            Translate {batchLanguages.length} language{batchLanguages.length !== 1 ? 's' : ''}
                        </LemonButton>
                    </div>
                </div>
            )}

            {addedLanguages.length > 0 && survey.questions.length > 1 && (
                <div className="border rounded p-3 space-y-3">
                    <h3 className="font-semibold text-sm">Translate selected questions</h3>
                    <div className="space-y-2">
                        <LemonSelect
                            options={COMMON_LANGUAGES.filter((l) => addedLanguages.includes(l.value)).map((l) => ({
                                value: l.value,
                                label: l.label,
                            }))}
                            onChange={(value) => setSelectedLanguageForQuestions(value)}
                            placeholder="Select target language"
                            value={selectedLanguageForQuestions}
                        />

                        <div className="space-y-1">
                            <div className="text-xs text-muted">Select questions to translate:</div>
                            <div className="space-y-1">
                                {survey.questions.map((question, idx) => (
                                    <LemonCheckbox
                                        key={idx}
                                        checked={selectedQuestions.includes(idx)}
                                        onChange={(checked) => {
                                            if (checked) {
                                                setSelectedQuestions([...selectedQuestions, idx])
                                            } else {
                                                setSelectedQuestions(selectedQuestions.filter((i) => i !== idx))
                                            }
                                        }}
                                        label={
                                            <span className="text-sm">
                                                Q{idx + 1}: {question.question || 'Untitled question'}
                                            </span>
                                        }
                                    />
                                ))}
                            </div>
                        </div>

                        <LemonButton
                            icon={<IconMagicWand />}
                            type="primary"
                            fullWidth
                            onClick={async (e) => {
                                if (selectedQuestions.length > 0 && selectedLanguageForQuestions) {
                                    const onlyChangedFields = !(e.ctrlKey || e.metaKey)
                                    // Translate each selected question
                                    for (const questionIndex of selectedQuestions) {
                                        await autoTranslateSurveyQuestion(
                                            questionIndex,
                                            selectedLanguageForQuestions,
                                            onlyChangedFields
                                        )
                                    }
                                    // Clear selection after successful translation
                                    setSelectedQuestions([])
                                }
                            }}
                            loading={translatingLanguage !== null && translatingLanguage !== 'batch'}
                            disabled={selectedQuestions.length === 0 || !selectedLanguageForQuestions || !survey.id}
                            disabledReason={
                                !survey.id
                                    ? 'Save the survey first before translating'
                                    : !selectedLanguageForQuestions
                                      ? 'Select a target language'
                                      : selectedQuestions.length === 0
                                        ? 'Select at least one question'
                                        : undefined
                            }
                        >
                            Translate {selectedQuestions.length} question{selectedQuestions.length !== 1 ? 's' : ''}
                        </LemonButton>
                    </div>
                </div>
            )}

            <div className="space-y-2">
                {addedLanguages.length > 0 && (
                    <div
                        className={`flex items-center justify-between px-2 py-1.5 border rounded cursor-pointer ${editingLanguage === null ? 'border-warning bg-warning-highlight' : 'border-border'}`}
                        onClick={() => setEditingLanguage(null)}
                    >
                        <span>Default (Original)</span>
                    </div>
                )}

                {addedLanguages.map((lang) => (
                    <div
                        key={lang}
                        className={`flex items-center justify-between px-2 py-1 border rounded cursor-pointer ${editingLanguage === lang ? 'border-warning bg-warning-highlight' : 'border-border'}`}
                        onClick={() => setEditingLanguage(lang)}
                    >
                        <div className="flex items-center gap-2">
                            <span>{COMMON_LANGUAGES.find((l) => l.value === lang)?.label || lang}</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <LemonButton
                                icon={<IconMagicWand />}
                                size="xsmall"
                                type="secondary"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    // Default: smart retranslation (only changed fields)
                                    // Ctrl/Cmd+click: full retranslation (all fields)
                                    const onlyChangedFields = !(e.ctrlKey || e.metaKey)
                                    autoTranslateSurvey(lang, onlyChangedFields)
                                }}
                                loading={translatingLanguage === lang}
                                tooltip="Retranslate only fields that changed in the original language. Ctrl+click to retranslate all fields."
                            />
                            <LemonButton
                                icon={<IconTrash />}
                                status="danger"
                                size="xsmall"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    LemonDialog.open({
                                        title: 'Delete translation',
                                        description: (
                                            <p className="py-2">
                                                Are you sure you want to delete the translation for{' '}
                                                <strong>
                                                    {COMMON_LANGUAGES.find((l) => l.value === lang)?.label || lang}
                                                </strong>
                                                ? All translated content for this language will be permanently lost.
                                            </p>
                                        ),
                                        primaryButton: {
                                            children: 'Delete',
                                            status: 'danger',
                                            onClick: () => removeLanguage(lang),
                                        },
                                        secondaryButton: {
                                            children: 'Cancel',
                                        },
                                    })
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
