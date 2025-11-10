"use client";

import React from 'react';
import { SessionProvider } from "@/components/app/session-provider";
import { RoomAudioRenderer, StartAudio } from '@livekit/components-react';
import { Toaster } from "@/components/ui/sonner";
import { AppConfig } from '@/app-config';

interface ClientProvidersProps {
  children: React.ReactNode;
  appConfig: AppConfig; 
}

export function ClientProviders({ children, appConfig }: ClientProvidersProps) {
  return (
    <>
      <SessionProvider appConfig={appConfig}>
        <StartAudio label="Start Audio" />
        <RoomAudioRenderer />
        {children}
      </SessionProvider>
      <Toaster />
    </>
  );
}