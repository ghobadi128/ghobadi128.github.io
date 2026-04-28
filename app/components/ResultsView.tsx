"use client";
import CopyButton from "./CopyButton";
import { GeneratedSequence } from "@/app/types";

function Section({
  title,
  tag,
  subject,
  body,
  charCount,
}: {
  title: string;
  tag?: string;
  subject?: string;
  body: string;
  charCount?: boolean;
}) {
  const copyText = subject ? `Subject: ${subject}\n\n${body}` : body;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm text-gray-800">{title}</h3>
          {tag && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 font-medium">
              {tag}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {charCount && (
            <span className="text-xs text-gray-400">{body.length} chars</span>
          )}
          <CopyButton text={copyText} />
        </div>
      </div>
      <div className="p-4 space-y-3">
        {subject && (
          <div>
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Subject
            </span>
            <p className="mt-0.5 text-sm font-medium text-gray-900">{subject}</p>
          </div>
        )}
        <div>
          {subject && (
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Body
            </span>
          )}
          <pre className="mt-0.5 text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed">
            {body}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default function ResultsView({ result }: { result: GeneratedSequence }) {
  const isActive =
    result.email2_body.length > 0 ||
    result.sms1.length > 0;

  return (
    <div className="space-y-6">
      {/* Diagnosis */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
        <h3 className="text-xs font-semibold text-amber-800 uppercase tracking-wide">
          Phase 1 Diagnosis (Internal)
        </h3>
        <div>
          <span className="text-xs font-medium text-amber-700">Problem:</span>
          <p className="text-sm text-amber-900 mt-0.5">{result.diagnosis_problem}</p>
        </div>
        <div>
          <span className="text-xs font-medium text-amber-700">Revenue angle:</span>
          <p className="text-sm text-amber-900 mt-0.5">{result.diagnosis_revenue}</p>
        </div>
      </div>

      {/* Emails */}
      <Section
        title="Email 1 — Cold Outreach"
        tag="Send today"
        subject={result.email1_subject}
        body={result.email1_body}
      />

      {isActive && (
        <>
          <Section
            title="Email 2 — Follow-Up"
            tag="Day 3"
            subject={result.email2_subject}
            body={result.email2_body}
          />
          <Section
            title="Email 3 — Soft Close"
            tag="Day 7"
            subject={result.email3_subject}
            body={result.email3_body}
          />

          {/* SMS */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
              <h3 className="font-semibold text-sm text-gray-800">SMS Sequence</h3>
              <CopyButton
                text={`SMS 1 (Day 1): ${result.sms1}\n\nSMS 2 (Day 4): ${result.sms2}\n\nSMS 3 (Day 8): ${result.sms3}`}
              />
            </div>
            <div className="divide-y divide-gray-100">
              {[
                { label: "SMS 1", tag: "Day 1", text: result.sms1 },
                { label: "SMS 2", tag: "Day 4", text: result.sms2 },
                { label: "SMS 3", tag: "Day 8", text: result.sms3 },
              ].map(({ label, tag, text }) => (
                <div key={label} className="px-4 py-3 flex items-start gap-3">
                  <div className="flex-shrink-0 flex items-center gap-1.5 pt-0.5">
                    <span className="text-xs font-semibold text-gray-700">{label}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
                      {tag}
                    </span>
                  </div>
                  <p className="flex-1 text-sm text-gray-800">{text}</p>
                  <div className="flex-shrink-0 flex items-center gap-2">
                    <span className="text-xs text-gray-400">{text.length}c</span>
                    <CopyButton text={text} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
