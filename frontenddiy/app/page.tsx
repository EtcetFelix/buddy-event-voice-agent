'use client';

import { useState } from 'react';
import { useSession } from '@/components/app/session-provider';

export default function Home() {
  const [transcript, setTranscript] = useState<Array<{ speaker: 'user' | 'buddy', text: string }>>([
    { speaker: 'user', text: 'Hey Buddy, what events are happening in North Beach?' },
    { speaker: 'buddy', text: "Hey! I'm doing great, especially when I get to hear about new adventures. Let me sniff around for events in North Beach for you!" },
    { speaker: 'user', text: 'Thanks!' },
  ]);
  const { appConfig, isSessionActive, startSession, endSession } = useSession();
  const isConnected = isSessionActive;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-orange-50">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        
        {/* Header with Buddy */}
        <div className="text-center mb-8">
          <div className="inline-block relative">
            <div className="w-32 h-32 bg-gradient-to-br from-white to-gray-100 rounded-full flex items-center justify-center text-6xl shadow-lg border-4 border-orange-200">
              🐕
            </div>
            {isConnected && (
              <div className="absolute -bottom-1 -right-1 w-8 h-8 bg-green-500 rounded-full border-4 border-white animate-pulse" />
            )}
          </div>
          <h1 className="text-5xl font-bold mt-4 text-gray-800">Buddy</h1>
          <p className="text-gray-600 text-lg">Your SF Events Companion</p>
        </div>

        {/* Call Controls */}
        <div className="flex gap-4 justify-center mb-8">
          {!isConnected ? (
            <button
              onClick={startSession}
              className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-full text-lg font-semibold shadow-lg transition-all hover:scale-105 flex items-center gap-2"
            >
              <span>🎤</span>
              Start Call
            </button>
          ) : (
            <button
              onClick={endSession}
              className="px-8 py-4 bg-red-600 hover:bg-red-700 text-white rounded-full text-lg font-semibold shadow-lg transition-all hover:scale-105 flex items-center gap-2"
            >
              <span>📞</span>
              End Call
            </button>
          )}
        </div>

        {/* Transcript Panel */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
          {/* Transcript Header */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 text-white">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <span>💬</span>
              Live Transcript
            </h2>
          </div>

          {/* Transcript Content */}
          <div className="h-96 overflow-y-auto p-6 space-y-4">
            {!isConnected && transcript.length === 0 ? (
              <div className="text-center text-gray-400 py-16">
                <p className="text-lg">Start a call to see the conversation transcript here</p>
              </div>
            ) : (
              transcript.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.speaker === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                      message.speaker === 'user'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-gray-100 text-gray-800 rounded-bl-none'
                    }`}
                  >
                    <div className="text-xs font-semibold mb-1 opacity-70">
                      {message.speaker === 'user' ? 'You' : 'Buddy'}
                    </div>
                    <p className="text-sm leading-relaxed">{message.text}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Connection Status */}
        <div className="mt-4 text-center">
          <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm ${
            isConnected 
              ? 'bg-green-100 text-green-800' 
              : 'bg-gray-100 text-gray-600'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-gray-400'
            }`} />
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>

      </div>
    </div>
  );
}