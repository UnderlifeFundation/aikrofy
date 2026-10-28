'use client';

import { useState, use } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowRight, Loader2, Download, Share2, Mail, MessageCircle, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';

// ── Symptom definitions (keyed to translation file) ──────────────────────
const SYMPTOM_GROUPS = [
    {
        category: 'symptomsDigestive',
        items: ['s1', 's2', 's3', 's4', 's5', 's6', 's7'],
    },
    {
        category: 'symptomsCardiovascular',
        items: ['s8', 's9', 's10', 's11', 's33'],
    },
    {
        category: 'symptomsMusculoskeletal',
        items: ['s12', 's13', 's14', 's15', 's16', 's17', 's18', 's19'],
    },
    {
        category: 'symptomsRespiratory',
        items: ['s20', 's21', 's22', 's23', 's24'],
    },
    {
        category: 'symptomsNeurological',
        items: ['s30', 's31', 's32'],
    },
    {
        category: 'symptomsGeneral',
        items: ['s25', 's26', 's27', 's28', 's29'],
    },
];

// ── Zod Schema ────────────────────────────────────────────────────────────
const evaluationSchema = z.object({
    // Step 1 – Personal
    age: z.string().min(1, 'Required'),
    gender: z.enum(['male', 'female', 'other']),
    // Step 2 – Measurements & Vitals
    height_cm: z.string().min(1, 'Required'),
    weight_kg: z.string().min(1, 'Required'),
    blood_pressure: z.string().optional(),
    pulse: z.string().optional(),
    energy_level: z.string().optional(),
    // Step 3 – Symptoms (managed outside zod via local state)
    // Step 4 – Lifestyle
    primary_goal: z.string().min(1, 'Required'),
    activity_level: z.enum(['sedentary', 'light', 'moderate', 'active', 'very_active']),
    meals_per_day: z.string().min(1, 'Required'),
    exercise_frequency: z.string().optional(),
    water_intake_liters: z.string().optional(),
    sleep_hours: z.string().optional(),
    sleep_quality: z.string().optional(),
    observations: z.string().optional(),
    // Step 5 – Contact
    first_name: z.string().min(2, 'Required'),
    email: z.string().email('Invalid email'),
    phone: z.string().min(8, 'Required'),
});

type EvaluationFormValues = z.infer<typeof evaluationSchema>;

const TOTAL_STEPS = 7; // intro(0) + personal(1) + body(2) + symptoms(3) + lifestyle(4) + contact(5) + results(6)

// ── Component ─────────────────────────────────────────────────────────────
export default function EvaluationPage({ params }: { params: Promise<{ company_id: string }> }) {
    const resolvedParams = use(params);
    const company_id = resolvedParams.company_id;
    const { t, i18n } = useTranslation();
    const [step, setStep] = useState(0);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
    const [resultData, setResultData] = useState<any>(null);

    // Fetch company public profile for language preference
    const { data: profile } = useQuery({
        queryKey: ['public-company', company_id],
        queryFn: async () => {
            const { data } = await apiClient.get(`/companies/public/${company_id}`);
            return data.data;
        },
    });

    useEffect(() => {
        if (profile?.language && i18n.language !== profile.language) {
            i18n.changeLanguage(profile.language);
        }
    }, [profile?.language, i18n]);

    const {
        register,
        handleSubmit,
        trigger,
        setValue,
        watch,
        formState: { errors },
    } = useForm<EvaluationFormValues>({
        resolver: zodResolver(evaluationSchema),
        mode: 'onChange',
    });

    // ── Symptom toggle helper ─────────────────────────────────────────────
    const toggleSymptom = (symptomKey: string) => {
        const label = t(`wellnessForm.${symptomKey}`);
        setSelectedSymptoms((prev) =>
            prev.includes(label) ? prev.filter((s) => s !== label) : [...prev, label]
        );
    };

    const isSymptomChecked = (symptomKey: string) =>
        selectedSymptoms.includes(t(`wellnessForm.${symptomKey}`));

    // ── Navigation ────────────────────────────────────────────────────────
    const nextStep = async () => {
        let fieldsToValidate: any[] = [];
        if (step === 1) fieldsToValidate = ['age', 'gender'];
        if (step === 2) fieldsToValidate = ['height_cm', 'weight_kg'];
        if (step === 4) fieldsToValidate = ['primary_goal', 'activity_level', 'meals_per_day'];

        if (fieldsToValidate.length > 0) {
            const isValid = await trigger(fieldsToValidate);
            if (!isValid) return;
        }
        setStep((s) => s + 1);
    };

    const prevStep = () => setStep((s) => s - 1);

    // ── Submit ────────────────────────────────────────────────────────────
    const onSubmit = async (values: EvaluationFormValues) => {
        setIsSubmitting(true);
        try {
            const payload = {
                ...values,
                age: Number(values.age),
                height_cm: Number(values.height_cm),
                weight_kg: Number(values.weight_kg),
                meals_per_day: Number(values.meals_per_day),
                pulse: values.pulse ? Number(values.pulse) : undefined,
                energy_level: values.energy_level ? Number(values.energy_level) : undefined,
                symptoms: selectedSymptoms,
            };
            const { data } = await apiClient.post(`/wellness/evaluate/${company_id}`, payload);
            setResultData(data.data);
            setStep(6); // go to results step
        } catch (err) {
            toast.error(t('common.error', { defaultValue: 'Submission failed. Please try again.' }));
        } finally {
            setIsSubmitting(false);
        }
    };

    // ── Results View ──────────────────────────────────────────────────────
    if (step === 6 && resultData) {
        return (
            <div className="mx-auto max-w-2xl px-4 py-12 space-y-6">
                <Card>
                    <CardHeader className="border-b text-center">
                        <CardTitle className="text-2xl">{t('wellnessForm.resultsTitle')}</CardTitle>
                        <CardDescription>
                            {t('wellnessForm.resultsDate')}: {new Date().toLocaleDateString(i18n.language, { year: 'numeric', month: 'long', day: 'numeric' })}
                        </CardDescription>
                    </CardHeader>

                    {/* Personal Data */}
                    <CardContent className="space-y-6 pt-6">
                        <section>
                            <h3 className="font-semibold text-lg mb-2">{t('wellnessForm.personalData')}</h3>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                                <p><span className="font-medium">{t('wellnessForm.firstName')}:</span> {resultData.first_name || '—'}</p>
                                <p><span className="font-medium">{t('wellnessForm.age')}:</span> {resultData.age}</p>
                                <p><span className="font-medium">{t('wellnessForm.gender')}:</span> {resultData.gender}</p>
                                <p><span className="font-medium">{t('wellnessForm.email')}:</span> {resultData.email || '—'}</p>
                            </div>
                        </section>

                        {/* Measurements */}
                        <section>
                            <h3 className="font-semibold text-lg mb-2">{t('wellnessForm.measurementsResult')}</h3>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                                <p><span className="font-medium">{t('wellnessForm.weight')}:</span> {resultData.weight_kg} kg</p>
                                <p><span className="font-medium">{t('wellnessForm.height')}:</span> {resultData.height_cm} cm</p>
                                <p><span className="font-medium">{t('wellnessForm.bmi')}:</span> {resultData.bmi}</p>
                                <p><span className="font-medium">{t('wellnessForm.bmiCategory')}:</span> {resultData.bmi_category}</p>
                                {resultData.blood_pressure && (
                                    <p><span className="font-medium">{t('wellnessForm.bloodPressure')}:</span> {resultData.blood_pressure}</p>
                                )}
                                {resultData.pulse && (
                                    <p><span className="font-medium">{t('wellnessForm.pulse')}:</span> {resultData.pulse}</p>
                                )}
                                {resultData.energy_level && (
                                    <p><span className="font-medium">{t('wellnessForm.energyLevel')}:</span> {resultData.energy_level}/10</p>
                                )}
                            </div>
                        </section>

                        {/* Reported Symptoms */}
                        <section>
                            <h3 className="font-semibold text-lg mb-2">{t('wellnessForm.reportedSymptoms')}</h3>
                            {resultData.symptoms && resultData.symptoms.length > 0 ? (
                                <ul className="list-disc pl-5 text-sm space-y-1">
                                    {resultData.symptoms.map((s: string, i: number) => (
                                        <li key={i}>{s}</li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="text-sm text-muted-foreground">{t('wellnessForm.noSymptoms')}</p>
                            )}
                        </section>

                        {/* AI Diagnosis */}
                        <section className="bg-muted/50 rounded-lg p-4">
                            <h3 className="font-semibold text-lg mb-2">{t('wellnessForm.diagnosisTitle')}</h3>
                            <p className="text-sm leading-relaxed">
                                {resultData.diagnosis || t('wellnessForm.noDiagnosis')}
                            </p>
                        </section>

                        {/* AI Recommendations */}
                        <section className="bg-green-50 dark:bg-green-950/20 rounded-lg p-4">
                            <h3 className="font-semibold text-lg mb-2">{t('wellnessForm.recommendationsTitle')}</h3>
                            <p className="text-sm leading-relaxed">
                                {resultData.recommendations || t('wellnessForm.noRecommendations')}
                            </p>
                        </section>
                    </CardContent>
                    
                    <CardFooter className="flex flex-col gap-6 pt-6 border-t">
                        {/* Action Buttons */}
                        <div className="flex flex-wrap justify-center gap-4 w-full">
                            <Button variant="outline" onClick={() => window.location.reload()} className="flex-1 min-w-[140px]">
                                {t('wellnessForm.startNew')}
                            </Button>
                            
                            {resultData.pdf_url && (
                                <Button 
                                    variant="secondary" 
                                    className="flex-1 min-w-[140px] bg-green-600 hover:bg-green-700 text-white border-none"
                                    onClick={() => window.open(resultData.pdf_url, '_blank')}
                                >
                                    <Download className="mr-2 h-4 w-4" /> {t('wellnessForm.downloadPDF')}
                                </Button>
                            )}
                            
                            {/* Share Dropdown logic (simplified for public page) */}
                            <div className="flex gap-2">
                                <Button 
                                    variant="outline" 
                                    title={t('wellnessForm.shareViaWhatsApp')}
                                    onClick={() => {
                                        const text = encodeURIComponent(`¡Hola! Mira mi análisis de bienestar 🌿: ${resultData.pdf_url}`);
                                        window.open(`https://wa.me/?text=${text}`, '_blank');
                                    }}
                                >
                                    <MessageCircle className="h-4 w-4 text-green-500" />
                                </Button>
                                <Button 
                                    variant="outline"
                                    title={t('wellnessForm.shareViaTelegram')}
                                    onClick={() => {
                                        const text = encodeURIComponent(`🌿 Mi análisis de bienestar: ${resultData.pdf_url}`);
                                        window.open(`https://t.me/share/url?url=${resultData.pdf_url}&text=${text}`, '_blank');
                                    }}
                                >
                                    <Send className="h-4 w-4 text-blue-400" />
                                </Button>
                            </div>
                        </div>

                        {/* Referral Section */}
                        <div className="w-full bg-muted/30 rounded-xl p-6 text-center space-y-4 border border-dashed">
                            <div className="space-y-1">
                                <h4 className="font-bold text-lg">{t('wellnessForm.inviteTitle')}</h4>
                                <p className="text-sm text-muted-foreground">{t('wellnessForm.inviteSubtitle')}</p>
                            </div>
                            <Button 
                                variant="default" 
                                className="w-full sm:w-auto"
                                onClick={() => {
                                    const distLink = `https://aikrofy.com/evaluate/${resultData.company_id}`;
                                    const text = encodeURIComponent(`${t('wellnessForm.inviteWhatsApp')} ${distLink}`);
                                    window.open(`https://wa.me/?text=${text}`, '_blank');
                                }}
                            >
                                <Share2 className="mr-2 h-4 w-4" /> {t('wellnessForm.inviteFriend')}
                            </Button>
                        </div>
                    </CardFooter>
                </Card>
            </div>
        );
    }

    // ── Form Progress ─────────────────────────────────────────────────────
    const progress = ((step + 1) / (TOTAL_STEPS - 1)) * 100; // exclude results as a counted step

    return (
        <div className="mx-auto flex max-w-lg flex-col px-4 py-8 md:py-12">
            {/* Progress */}
            <div className="mb-8 space-y-2">
                <Progress value={progress} className="h-2" />
                <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{t('wellnessForm.step')} {step + 1} / {TOTAL_STEPS - 1}</span>
                </div>
            </div>

            <Card>
                <form onSubmit={handleSubmit(onSubmit)}>
                    {/* ── Step 0: Intro ─────────────────────────────────────── */}
                    {step === 0 && (
                        <>
                            <CardHeader>
                                <CardTitle className="text-2xl">{t('wellnessForm.title')}</CardTitle>
                                <CardDescription>{t('wellnessForm.subtitle')}</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ul className="space-y-2 text-sm">
                                    <li className="flex items-center gap-2">🔹 {t('wellnessForm.bullet1')}</li>
                                    <li className="flex items-center gap-2">🔹 {t('wellnessForm.bullet2')}</li>
                                    <li className="flex items-center gap-2">🔹 {t('wellnessForm.bullet3')}</li>
                                </ul>
                            </CardContent>
                            <CardFooter className="pt-8">
                                <Button type="button" onClick={() => setStep(1)} className="w-full">
                                    {t('wellnessForm.startNow')} <ArrowRight className="ml-2 h-4 w-4" />
                                </Button>
                            </CardFooter>
                        </>
                    )}

                    {/* ── Step 1: Personal ──────────────────────────────────── */}
                    {step === 1 && (
                        <>
                            <CardHeader><CardTitle>{t('wellnessForm.aboutYou')}</CardTitle></CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>{t('wellnessForm.age')}</Label>
                                    <Input type="number" {...register('age')} placeholder="e.g. 30" />
                                    {errors.age && <p className="text-xs text-destructive">{errors.age.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('wellnessForm.gender')}</Label>
                                    <RadioGroup onValueChange={(v) => setValue('gender', v as any)} defaultValue={watch('gender')}>
                                        <div className="flex items-center space-x-2">
                                            <RadioGroupItem value="female" id="r1" />
                                            <Label htmlFor="r1">{t('wellnessForm.female')}</Label>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            <RadioGroupItem value="male" id="r2" />
                                            <Label htmlFor="r2">{t('wellnessForm.male')}</Label>
                                        </div>
                                    </RadioGroup>
                                    {errors.gender && <p className="text-xs text-destructive">{errors.gender.message}</p>}
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-between pt-6">
                                <Button type="button" variant="outline" onClick={prevStep}>{t('wellnessForm.back')}</Button>
                                <Button type="button" onClick={nextStep}>{t('wellnessForm.next')} <ArrowRight className="ml-2 h-4 w-4" /></Button>
                            </CardFooter>
                        </>
                    )}

                    {/* ── Step 2: Measurements & Vitals ────────────────────── */}
                    {step === 2 && (
                        <>
                            <CardHeader><CardTitle>{t('wellnessForm.measurements')}</CardTitle></CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.height')}</Label>
                                        <Input type="number" {...register('height_cm')} placeholder="170" />
                                        {errors.height_cm && <p className="text-xs text-destructive">{errors.height_cm.message}</p>}
                                    </div>
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.weight')}</Label>
                                        <Input type="number" {...register('weight_kg')} placeholder="70" />
                                        {errors.weight_kg && <p className="text-xs text-destructive">{errors.weight_kg.message}</p>}
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('wellnessForm.bloodPressure')}</Label>
                                    <Input {...register('blood_pressure')} placeholder={t('wellnessForm.bloodPressurePlaceholder')} />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.pulse')}</Label>
                                        <Input type="number" {...register('pulse')} placeholder={t('wellnessForm.pulsePlaceholder')} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.energyLevel')}</Label>
                                        <Input type="number" min={1} max={10} {...register('energy_level')} placeholder="5" />
                                    </div>
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-between pt-6">
                                <Button type="button" variant="outline" onClick={prevStep}>{t('wellnessForm.back')}</Button>
                                <Button type="button" onClick={nextStep}>{t('wellnessForm.next')} <ArrowRight className="ml-2 h-4 w-4" /></Button>
                            </CardFooter>
                        </>
                    )}

                    {/* ── Step 3: Symptoms ──────────────────────────────────── */}
                    {step === 3 && (
                        <>
                            <CardHeader>
                                <CardTitle>{t('wellnessForm.symptomsTitle')}</CardTitle>
                                <CardDescription>{t('wellnessForm.symptomsSubtitle')}</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-6">
                                {SYMPTOM_GROUPS.map((group) => (
                                    <div key={group.category}>
                                        <h4 className="font-semibold text-sm mb-2 text-muted-foreground uppercase tracking-wide">
                                            {t(`wellnessForm.${group.category}`)}
                                        </h4>
                                        <div className="grid grid-cols-1 gap-2">
                                            {group.items.map((key) => (
                                                <label
                                                    key={key}
                                                    className="flex items-center gap-3 rounded-md border p-2.5 text-sm cursor-pointer hover:bg-accent transition-colors"
                                                >
                                                    <Checkbox
                                                        checked={isSymptomChecked(key)}
                                                        onCheckedChange={() => toggleSymptom(key)}
                                                    />
                                                    {t(`wellnessForm.${key}`)}
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-between pt-6">
                                <Button type="button" variant="outline" onClick={prevStep}>{t('wellnessForm.back')}</Button>
                                <Button type="button" onClick={nextStep}>{t('wellnessForm.next')} <ArrowRight className="ml-2 h-4 w-4" /></Button>
                            </CardFooter>
                        </>
                    )}

                    {/* ── Step 4: Lifestyle & Goals ─────────────────────────── */}
                    {step === 4 && (
                        <>
                            <CardHeader><CardTitle>{t('wellnessForm.lifestyle')}</CardTitle></CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>{t('wellnessForm.primaryGoal')}</Label>
                                    <Input {...register('primary_goal')} placeholder={t('wellnessForm.goalPlaceholder')} />
                                    {errors.primary_goal && <p className="text-xs text-destructive">{errors.primary_goal.message}</p>}
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.activityLevel')}</Label>
                                        <select
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                                            {...register('activity_level')}
                                        >
                                            <option value="sedentary">{t('wellnessForm.sedentary')}</option>
                                            <option value="light">{t('wellnessForm.light')}</option>
                                            <option value="moderate">{t('wellnessForm.moderate')}</option>
                                            <option value="active">{t('wellnessForm.active')}</option>
                                            <option value="very_active">{t('wellnessForm.veryActive')}</option>
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.exerciseFrequency')}</Label>
                                        <Input {...register('exercise_frequency')} placeholder="e.g. 3 times/week" />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.mealsPerDay')}</Label>
                                        <Input type="number" {...register('meals_per_day')} placeholder="3" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.waterIntake')}</Label>
                                        <Input type="number" step="0.1" {...register('water_intake_liters')} placeholder="2.5" />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.sleepHours')}</Label>
                                        <Input type="number" {...register('sleep_hours')} placeholder="7" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>{t('wellnessForm.sleepQuality')}</Label>
                                        <select
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                                            {...register('sleep_quality')}
                                        >
                                            <option value="excellent">{t('wellnessForm.sleepExcellent')}</option>
                                            <option value="good">{t('wellnessForm.sleepGood')}</option>
                                            <option value="fair">{t('wellnessForm.sleepFair')}</option>
                                            <option value="poor">{t('wellnessForm.sleepPoor')}</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('wellnessForm.observations')}</Label>
                                    <textarea
                                        className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                                        {...register('observations')}
                                        placeholder={t('wellnessForm.observationsPlaceholder')}
                                        rows={3}
                                    />
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-between pt-6">
                                <Button type="button" variant="outline" onClick={prevStep}>{t('wellnessForm.back')}</Button>
                                <Button type="button" onClick={nextStep}>{t('wellnessForm.next')} <ArrowRight className="ml-2 h-4 w-4" /></Button>
                            </CardFooter>
                        </>
                    )}

                    {/* ── Step 5: Contact ───────────────────────────────────── */}
                    {step === 5 && (
                        <>
                            <CardHeader>
                                <CardTitle>{t('wellnessForm.almostDone')}</CardTitle>
                                <CardDescription>{t('wellnessForm.whereToSend')}</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>{t('wellnessForm.firstName')}</Label>
                                    <Input {...register('first_name')} placeholder="Jane" />
                                    {errors.first_name && <p className="text-xs text-destructive">{errors.first_name.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('wellnessForm.email')}</Label>
                                    <Input type="email" {...register('email')} placeholder="jane@example.com" />
                                    {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('wellnessForm.phone')}</Label>
                                    <Input type="tel" {...register('phone')} placeholder="+1 234 567 8900" />
                                    {errors.phone && <p className="text-xs text-destructive">{errors.phone.message}</p>}
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-between pt-6">
                                <Button type="button" variant="outline" onClick={prevStep}>{t('wellnessForm.back')}</Button>
                                <Button type="submit" disabled={isSubmitting}>
                                    {isSubmitting ? (
                                        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('wellnessForm.analyzing')}</>
                                    ) : (
                                        t('wellnessForm.getResults')
                                    )}
                                </Button>
                            </CardFooter>
                        </>
                    )}
                </form>
            </Card>
        </div>
    );
}
