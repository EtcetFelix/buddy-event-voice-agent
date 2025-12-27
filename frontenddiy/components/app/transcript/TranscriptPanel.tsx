'use client';

import { useEffect, useRef } from 'react';

type SimpleTranscriptMessage = { speaker: 'user' | 'buddy', text: string };

interface TranscriptPanelProps {
  transcript: SimpleTranscriptMessage[];
  isConnected: boolean;
  hasLiveMessages: boolean;
}

export default function TranscriptPanel({ 
  transcript, 
  isConnected, 
  hasLiveMessages 
}: TranscriptPanelProps) {
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcript]);

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
      {/* Transcript Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 text-white">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <span>💬</span>
          Live Transcript
        </h2>
      </div>

      {/* Transcript Content */}
      <div 
        ref={containerRef}
        className="h-96 overflow-y-auto p-6 space-y-4"
      >
        {!isConnected && !hasLiveMessages ? (
          <div className="text-center text-gray-400 py-16">
            <p className="text-lg">Start a call to see the conversation transcript here</p>
          </div>
        ) : (
          <>
            {transcript.map((message, index) => (
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
            ))}
            {/* Invisible element at the end for scrolling */}
            <div ref={transcriptEndRef} />
          </>
        )}
      </div>
    </div>
  );
}