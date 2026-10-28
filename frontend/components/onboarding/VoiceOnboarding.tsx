'use client';

import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Mic, Square, Loader2, CheckCircle2 } from 'lucide-react';
import Cookies from 'js-cookie';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import apiClient from '@/lib/api-client';

export function VoiceOnboarding() {
  const { t } = useTranslation();
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      if (audioPreviewUrl) {
        URL.revokeObjectURL(audioPreviewUrl);
        setAudioPreviewUrl(null);
      }
      setRecordedBlob(null);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        if (chunksRef.current.length > 0) {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
          setRecordedBlob(blob);
          const preview = URL.createObjectURL(blob);
          setAudioPreviewUrl(preview);
        }
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error(err);
      toast.error(t('onboarding.toastMicrophone', 'No se pudo acceder al micrófono. Por favor permite el acceso al micrófono en tu navegador.'));
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const discardRecording = () => {
    if (audioPreviewUrl) {
      URL.revokeObjectURL(audioPreviewUrl);
      setAudioPreviewUrl(null);
    }
    setRecordedBlob(null);
    chunksRef.current = [];
    toast.info('Nota de voz descartada');
  };

  const sendRecording = async () => {
    if (!recordedBlob) return;
    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append('audio', recordedBlob, 'onboarding_voice.webm');

      const response = await apiClient.post('/companies/voice-onboarding', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setIsSuccess(true);
      toast.success(t('onboarding.successTitle', '¡Ecosistema Configurado con Éxito!'));
      
      // Mark voice onboarding as completed so Tour starts smoothly on /agents
      sessionStorage.setItem('aikrofy_start_agent_tour', 'true');
      
      setTimeout(() => {
        window.location.href = "/agents";
      }, 2000);
      
    } catch (error: any) {
      console.error("Upload error:", error);
      const errMsg = error.response?.data?.error || error.message || t('onboarding.errorProcessing', 'Error procesando el audio');
      toast.error(errMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  if (isSuccess) {
    return (
      <Card className="w-full max-w-md mx-auto border-emerald-500 bg-emerald-500/10 shadow-2xl animate-fade-in">
        <CardContent className="flex flex-col items-center justify-center p-8 space-y-4">
          <CheckCircle2 className="w-16 h-16 text-emerald-500 animate-bounce" />
          <h2 className="text-xl font-bold text-center text-foreground">{t('onboarding.successTitle', '¡Ecosistema Configurado!')}</h2>
          <p className="text-center text-xs sm:text-sm text-muted-foreground">
            {t('onboarding.successDesc', 'Tus agentes, integraciones y reglas han sido creados mágicamente por tu CTO IA. Redirigiendo a tu panel de Agentes...')}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md mx-auto shadow-2xl border-primary/30 bg-card/95 backdrop-blur-xl relative overflow-hidden">
      {/* Visual top indicator badge */}
      <div className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 p-1 text-center">
        <div className="text-[10px] font-bold text-white uppercase tracking-widest flex items-center justify-center gap-1.5">
          <span>✨ Fase de Configuración Mágica</span>
        </div>
      </div>

      <CardHeader className="text-center pb-2 pt-4 px-4 sm:px-6">
        <CardTitle className="text-xl sm:text-2xl font-black tracking-tight text-foreground flex items-center justify-center gap-2">
          <span>Onboarding Mágico</span>
          <span className="text-xl">🎙️</span>
        </CardTitle>
        <CardDescription className="text-xs text-muted-foreground pt-1 leading-relaxed max-w-sm mx-auto">
          {t('onboarding.onboardingDesc', 'Cuéntale a tu CTO IA sobre tu negocio, tus productos y reglas. La IA creará tus agentes automáticamente.')}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-col items-center justify-center space-y-4 py-4 px-4 sm:px-6">
        {/* State 1: Recorded Preview with Confirm / Discard actions */}
        {recordedBlob && !isProcessing && (
          <div className="w-full space-y-3 animate-fade-in">
            <div className="p-3.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex flex-col items-center gap-2 text-center">
              <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                <span>🎧</span> Nota de voz grabada lista para procesar
              </span>
              {audioPreviewUrl && (
                <audio controls src={audioPreviewUrl} className="h-8 w-full max-w-xs mt-1" />
              )}
            </div>

            {/* Minimalist Action Controls */}
            <div className="flex items-center justify-center gap-3 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={discardRecording}
                className="rounded-xl border-destructive/30 text-destructive hover:bg-destructive/10 text-xs font-semibold px-4 cursor-pointer"
              >
                🗑️ Eliminar y Regrabar
              </Button>
              <Button
                size="sm"
                onClick={sendRecording}
                className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-xl text-xs font-bold px-5 cursor-pointer shadow-md shadow-indigo-500/20"
              >
                🚀 Enviar Nota de Voz
              </Button>
            </div>
          </div>
        )}

        {/* State 2: Normal Recording State */}
        {!recordedBlob && (
          <>
            {/* Prominent Micro Hint Arrow Banner */}
            {!isRecording && !isProcessing && (
              <div className="w-full p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/25 text-indigo-600 dark:text-indigo-400 text-xs font-semibold text-center animate-pulse flex items-center justify-center gap-1.5">
                <span>👇</span>
                <span>Toca el micrófono para comenzar a hablar</span>
                <span>👇</span>
              </div>
            )}

            <div className="relative py-2">
              {isRecording && (
                <div className="absolute -inset-4 bg-red-500/25 rounded-full animate-ping" />
              )}
              
              <Button
                size="lg"
                variant={isRecording ? "destructive" : "default"}
                className={`w-24 h-24 sm:w-28 sm:h-28 rounded-full transition-all duration-300 cursor-pointer ${
                  isRecording 
                    ? 'scale-105 shadow-red-500/50 shadow-2xl bg-red-600 hover:bg-red-700' 
                    : 'hover:scale-105 shadow-primary/40 shadow-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-600 hover:opacity-95'
                }`}
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isProcessing}
              >
                {isProcessing ? (
                  <Loader2 className="w-10 h-10 animate-spin text-white" />
                ) : isRecording ? (
                  <Square className="w-9 h-9 text-white animate-pulse" />
                ) : (
                  <Mic className="w-10 h-10 sm:w-12 sm:h-12 text-white" />
                )}
              </Button>
            </div>
          </>
        )}
        
        <div className="text-center min-h-[36px] flex items-center justify-center">
          {isProcessing ? (
            <div className="space-y-0.5">
              <p className="text-primary font-bold text-xs sm:text-sm animate-pulse">{t('onboarding.processing', 'Analizando negocio y configurando agentes...')}</p>
              <p className="text-[10px] text-muted-foreground">Estructurando prompts, skills de ventas y herramientas RAG</p>
            </div>
          ) : isRecording ? (
            <div className="space-y-0.5">
              <p className="text-red-500 font-bold text-xs sm:text-sm animate-pulse">{t('onboarding.recording', '🔴 Grabando... Toca de nuevo para finalizar')}</p>
              <p className="text-[10px] text-muted-foreground">Habla sobre tu catálogo, precios y políticas.</p>
            </div>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

