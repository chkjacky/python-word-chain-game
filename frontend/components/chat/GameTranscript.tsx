"use client";

import { ErrorBanner } from "@/components/chat/ErrorBanner";
import { ScoreChip } from "@/components/chat/ScoreChip";
import type { TranscriptItem } from "@/components/chat/types";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { Message, MessageContent } from "@/components/ui/message";
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";
import type { Difficulty } from "@/lib/types";

export function GameTranscript({
  items,
  difficulty,
}: {
  items: TranscriptItem[];
  difficulty: Difficulty;
}) {
  return (
    <MessageScrollerProvider>
      <MessageScroller className="flex-1">
        <MessageScrollerViewport>
          <MessageScrollerContent className="px-4 py-4">
            {items.map((item) => (
              <MessageScrollerItem
                key={item.id}
                messageId={item.id}
                scrollAnchor={item.role === "player"}
              >
                <Message align={item.role === "player" ? "end" : "start"}>
                  <MessageContent>
                    <Bubble
                      align={item.role === "player" ? "end" : "start"}
                      variant={
                        item.reason
                          ? "destructive"
                          : item.role === "player"
                            ? "default"
                            : "secondary"
                      }
                    >
                      <BubbleContent>{item.word}</BubbleContent>
                    </Bubble>
                    {item.breakdown && item.scoreDelta !== undefined && (
                      <ScoreChip
                        delta={item.scoreDelta}
                        breakdown={item.breakdown}
                      />
                    )}
                    {item.reason && (
                      <ErrorBanner
                        reason={item.reason}
                        difficulty={difficulty}
                        lastLetter={item.lastLetterAtSubmit}
                      />
                    )}
                  </MessageContent>
                </Message>
              </MessageScrollerItem>
            ))}
          </MessageScrollerContent>
        </MessageScrollerViewport>
        <MessageScrollerButton />
      </MessageScroller>
    </MessageScrollerProvider>
  );
}
