'use client';

import React, { useState } from 'react';
import { LiveKitRoom, VideoConference, RoomAudioRenderer } from '@livekit/components-react';
import '@livekit/components-styles';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Mic, Video, Users } from 'lucide-react';
import apiClient from '@/lib/api-client';

export default function LivekitTestPage() {
  const [roomUrl, setRoomUrl] = useState(process.env.NEXT_PUBLIC_LIVEKIT_URL || 'wss://your-project.livekit.cloud');
  const [token, setToken] = useState('');
  const [roomName, setRoomName] = useState('aikrofy-test-room');
  const [connected, setConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const requestToken = async () => {
    setIsLoading(true);
    try {
      // Se asume que el backend proveerá la creación del token REST
      const response = await apiClient.post('/livekit/token', {
        room_name: roomName,
        participant_name: 'Admin_Supervisor'
      });
      if (response.data && response.data.token) {
        setToken(response.data.token);
      }
    } catch (error) {
       console.error("No se pudo obtener el token (verificar flask endpoints)", error);
       alert("Error buscando el token. Ver consola para talles (CORS o endpoints incorrectos).");
    } finally {
      setIsLoading(false);
    }
  };

  const connectToRoom = () => {
      if(!token) return;
      setConnected(true);
  };

  return (
    <div className="container mx-auto max-w-6xl p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 flex flex-row items-center gap-2"><Video className="text-blue-500"/> LiveKit AI Voice Agent Sandbox</h1>
        <p className="text-muted-foreground">Entorno de testing WebRTC. Obtén tu token de LiveKit y comunícate con el bot en tiempo real.</p>
      </div>

      {!connected ? (
          <Card className="max-w-md mx-auto mt-10">
            <CardHeader>
               <CardTitle>Conexión a la Sala</CardTitle>
               <CardDescription>Genera un token temporal contra tu backend de Aikrofy</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium">Nombre de Sala</label>
                    <Input value={roomName} onChange={e => setRoomName(e.target.value)} placeholder="Ej: test-room" />
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium">Livekit Server URL</label>
                    <Input value={roomUrl} onChange={e => setRoomUrl(e.target.value)} placeholder="wss://..." disabled />
                </div>
                 <div className="space-y-2">
                    <label className="text-sm font-medium">Token Resultante (Auto generado)</label>
                    <Input value={token} onChange={e => setToken(e.target.value)} placeholder="eyJh..." />
                </div>
                
                <div className="flex gap-2 pt-4">
                    <Button variant="outline" className="flex-1" onClick={requestToken} disabled={isLoading}>
                       {isLoading ? 'Obteniendo...' : 'Solicitar a Flask (API)'}
                    </Button>
                    <Button className="flex-1 bg-green-600 hover:bg-green-700 text-white" onClick={connectToRoom} disabled={!token}>
                        Conectar WebRTC
                    </Button>
                </div>
            </CardContent>
          </Card>
      ) : (
          <Card className="shadow-lg h-[70vh] flex flex-col overflow-hidden border-0">
             <LiveKitRoom
                video={true}
                audio={true}
                token={token}
                serverUrl={roomUrl}
                data-lk-theme="default"
                className="h-full flex-1"
                onDisconnected={() => setConnected(false)}
             >
                {/* Visualización default predefinida de videoconferencia */}
                <VideoConference />
                <RoomAudioRenderer />
             </LiveKitRoom>
          </Card>
      )}
    </div>
  );
}
