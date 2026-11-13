'use client';

import React, { useState, useEffect, useCallback } from 'react';
import type { Conversation, Message, MessageSource } from '../src/contracts';
import { Header } from '../src/components/Header';
import { ConversationArea } from '../src/components/ConversationArea';
import { Composer } from '../src/components/Composer';
import { HistoryDrawer } from '../src/components/HistoryDrawer';
import { SettingsView } from '../src/components/SettingsView';

export default function Home() {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState<string>('');
  const [cancelSignal, setCancelSignal] = useState<number>(0);
  const [recordingStatus, setRecordingStatus] = useState<
    'idle' | 'recording' | 'transcribing'
  >('idle');
  const [selectedMicrophoneId, setSelectedMicrophoneId] = useState<string | undefined>(undefined);
  const [maxRecordSeconds, setMaxRecordSeconds] = useState<number>(120);

  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);

  const refreshSettings = useCallback(() => {
    fetch('/api/settings')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (typeof data?.selectedMicrophoneId === 'string') {
          setSelectedMicrophoneId(data.selectedMicrophoneId);
        }
        if (typeof data?.maxRecordSeconds === 'number') {
          setMaxRecordSeconds(data.maxRecordSeconds);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshSettings();
  }, [refreshSettings]);

  // Send message handler (First message creates conversation; subsequent appends)
  async function handleSendMessage(
    text: string,
    sources: MessageSource[]
  ): Promise<boolean> {
    try {
      if (!conversation) {
        // First message of conversation
        const response = await fetch('/api/conversations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, sources }),
        });

        if (!response.ok) {
          return false;
        }

        const data: { conversation: Conversation; message: Message } =
          await response.json();
        setConversation(data.conversation);
        setMessages([data.message]);
        return true;
      } else {
        // Subsequent message in existing conversation
        const response = await fetch(
          `/api/conversations/${encodeURIComponent(conversation.id)}/messages`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, sources }),
          }
        );

        if (!response.ok) {
          return false;
        }

        const newMessage: Message = await response.json();
        setMessages((prev) => [...prev, newMessage]);
        return true;
      }
    } catch {
      return false;
    }
  }

  // Conversation title rename handler
  async function handleRename(newTitle: string) {
    if (!conversation) return;
    try {
      const response = await fetch(
        `/api/conversations/${encodeURIComponent(conversation.id)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: newTitle }),
        }
      );

      if (response.ok) {
        const updated: Conversation = await response.json();
        setConversation(updated);
      }
    } catch {
      // Revert / ignore on error
    }
  }

  // History Drawer openers / actions
  function handleOpenHistory() {
    // Opening drawer does NOT interrupt in-flight recording or transcribing
    setIsHistoryOpen(true);
  }

  function handleCloseHistory() {
    setIsHistoryOpen(false);
  }

  async function handleSelectConversation(id: string) {
    if (conversation && conversation.id === id) {
      // Tapping the active conversation closes drawer without discarding draft or cancelling recording
      setIsHistoryOpen(false);
      return;
    }
    setCancelSignal((prev) => prev + 1);
    setDraft('');
    try {
      const res = await fetch(`/api/conversations/${encodeURIComponent(id)}`);
      if (res.ok) {
        const data: { conversation: Conversation; messages: Message[] } =
          await res.json();
        setConversation(data.conversation);
        setMessages(data.messages);
      }
    } catch {
      // Ignore fetch error
    } finally {
      setIsHistoryOpen(false);
    }
  }

  function handleNewConversation() {
    if (
      !conversation &&
      messages.length === 0 &&
      draft === '' &&
      recordingStatus === 'idle'
    ) {
      // Screen is already blank and idle: simply closes drawer per spec
      setIsHistoryOpen(false);
      return;
    }
    // Cancel in-flight recording, clear draft and start fresh blank conversation
    setCancelSignal((prev) => prev + 1);
    setDraft('');
    setConversation(null);
    setMessages([]);
    setIsHistoryOpen(false);
  }

  // Settings View openers / actions
  function handleOpenSettings() {
    // Cancels in-flight recording or transcribing, but preserves draft
    setCancelSignal((prev) => prev + 1);
    setIsSettingsOpen(true);
  }

  function handleCloseSettings() {
    setIsSettingsOpen(false);
    refreshSettings();
  }

  function handleActiveConversationDeleted() {
    setConversation(null);
    setMessages([]);
    setDraft('');
  }

  return (
    <main className="flex h-screen w-full flex-col bg-[#F5F7F9] text-[#18212B] overflow-hidden">
      {/* Top Header */}
      <Header
        title={conversation ? conversation.title : 'Hội thoại mới'}
        isNew={conversation === null || messages.length === 0}
        onRename={handleRename}
        onOpenHistory={handleOpenHistory}
        onOpenSettings={handleOpenSettings}
      />

      {/* Main Conversation Message Area */}
      <ConversationArea messages={messages} />

      {/* Shared Bottom Composer */}
      <Composer
        onSendMessage={handleSendMessage}
        draft={draft}
        onDraftChange={setDraft}
        cancelSignal={cancelSignal}
        onRecordingStateChange={setRecordingStatus}
        selectedMicrophoneId={selectedMicrophoneId}
        maxRecordSeconds={maxRecordSeconds}
      />

      {/* History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={handleCloseHistory}
        activeConversationId={conversation?.id}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />

      {/* Settings View */}
      <SettingsView
        isOpen={isSettingsOpen}
        onClose={handleCloseSettings}
        activeConversationId={conversation?.id}
        onActiveConversationDeleted={handleActiveConversationDeleted}
        onSettingsSaved={refreshSettings}
      />
    </main>
  );
}
