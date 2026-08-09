"use client";

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/**
 * Prop type definitions for the ClarificationModal component.
 */
interface ClarificationModalProps {
  /** Flag showing if the modal should be visible */
  isOpen: boolean;
  /** List of questions needing clarification from the user */
  questions: string[];
  /** Callback triggered when the user saves/submits their responses */
  onSubmit: (answers: Record<string, string>) => void;
  /** Callback triggered if the user decides to cancel or close the modal */
  onClose: () => void;
}

/**
 * Dialog modal component that prompts the user for answers during a
 * AWAITING_CLARIFICATION session status state.
 *
 * @param props - Dialog property hooks and list parameters.
 */
export function ClarificationModal({
  isOpen,
  questions,
  onSubmit,
  onClose,
}: ClarificationModalProps) {
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});

  // Reset form answers when new questions are received
  useEffect(() => {
    const initialAnswers: Record<string, string> = {};
    questions.forEach((question, index) => {
      initialAnswers[index.toString()] = "";
    });
    setUserAnswers(initialAnswers);
  }, [questions]);

  /**
   * Tracks and updates individual input values in form state.
   */
  const handleInputChange = (questionIndex: number, textValue: string) => {
    setUserAnswers((previousAnswers) => ({
      ...previousAnswers,
      [questionIndex.toString()]: textValue,
    }));
  };

  /**
   * Validates form and passes responses upward.
   */
  const handleFormSubmission = (event: React.FormEvent) => {
    event.preventDefault();
    
    // Map question text keys to user input answer values
    const responsePayload: Record<string, string> = {};
    questions.forEach((question, index) => {
      responsePayload[question] = userAnswers[index.toString()] || "";
    });

    onSubmit(responsePayload);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-[500px] bg-slate-900 border border-slate-800 text-slate-100 shadow-2xl backdrop-blur-md rounded-xl">
        <form onSubmit={handleFormSubmission}>
          <DialogHeader>
            <DialogTitle className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-amber-400 to-orange-500">
              🤔 Clarification Required
            </DialogTitle>
            <DialogDescription className="text-slate-400 mt-2">
              The agent requires some additional context about your business process or idea to draft a precise plan.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {questions.map((question, index) => (
              <div key={index} className="space-y-2">
                <label className="text-sm font-semibold text-slate-300">
                  {question}
                </label>
                <Input
                  type="text"
                  placeholder="Provide details..."
                  value={userAnswers[index.toString()] || ""}
                  onChange={(e) => handleInputChange(index, e.target.value)}
                  className="bg-slate-950 border-slate-800 text-slate-100 placeholder:text-slate-600 focus:ring-amber-500 focus:border-amber-500 rounded-lg"
                  required
                />
              </div>
            ))}
          </div>

          <DialogFooter className="mt-4 gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-gradient-to-r from-amber-500 to-orange-600 text-slate-950 font-bold hover:from-amber-600 hover:to-orange-700 rounded-lg px-6"
            >
              Resume Agent
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
