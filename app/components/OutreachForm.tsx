"use client";
import { useState } from "react";
import { DispensaryData } from "@/app/types";
import { buildPrompt } from "@/app/lib/buildPrompt";
import CopyButton from "./CopyButton";

const EMPTY: DispensaryData = {
  first_names: "",
  business_legal: "",
  business_dba: "",
  city: "",
  state: "California",
  zip: "",
  address: "",
  license_status: "Active",
  license_type: "Retailer",
  license_designation: "Adult-Use",
  issue_date: "",
  expiration_date: "",
  business_structure: "LLC",
  owner_names: "",
  activity: "",
  email: "",
  phone: "",
};

const AI_LINKS = [
  { label: "Claude.ai", href: "https://claude.ai/new", color: "bg-orange-500 hover:bg-orange-600" },
  { label: "ChatGPT", href: "https://chatgpt.com/", color: "bg-emerald-600 hover:bg-emerald-700" },
  { label: "Gemini", href: "https://gemini.google.com/", color: "bg-blue-600 hover:bg-blue-700" },
];

function Field({
  label,
  name,
  value,
  onChange,
  type = "text",
  placeholder,
  required,
  hint,
}: {
  label: string;
  name: keyof DispensaryData;
  value: string;
  onChange: (name: keyof DispensaryData, value: string) => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
  hint?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
        {hint && <span className="ml-1 font-normal text-gray-400">({hint})</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(name, e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
      />
    </div>
  );
}

function SelectField({
  label,
  name,
  value,
  options,
  onChange,
  required,
}: {
  label: string;
  name: keyof DispensaryData;
  value: string;
  options: string[];
  onChange: (name: keyof DispensaryData, value: string) => void;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(name, e.target.value)}
        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent bg-white"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function OutreachForm() {
  const [form, setForm] = useState<DispensaryData>(EMPTY);
  const [prompt, setPrompt] = useState<string | null>(null);

  const handleChange = (name: keyof DispensaryData, value: string) => {
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPrompt(buildPrompt(form));
    setTimeout(() => {
      document.getElementById("prompt-output")?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  };

  const handleReset = () => {
    setForm(EMPTY);
    setPrompt(null);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl font-bold text-brand-700">Paytree</span>
          <span className="text-gray-400 text-sm font-medium">/ Cold Outreach Generator</span>
        </div>
        <p className="text-sm text-gray-500">
          Fill in the dispensary data, then copy the generated prompt and paste it into any free AI chat.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Business Identity */}
        <fieldset className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <legend className="text-sm font-semibold text-gray-800 px-1">Business Identity</legend>
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Owner First Name(s)"
              name="first_names"
              value={form.first_names}
              onChange={handleChange}
              placeholder="e.g. Joshua, Maria"
              hint="comma-separated"
            />
            <Field
              label="DBA Name"
              name="business_dba"
              value={form.business_dba}
              onChange={handleChange}
              placeholder="e.g. Oakanna"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Legal Entity Name"
              name="business_legal"
              value={form.business_legal}
              onChange={handleChange}
              placeholder="e.g. Oakanna Inc."
            />
            <SelectField
              label="Business Structure"
              name="business_structure"
              value={form.business_structure}
              options={["LLC", "Corporation", "Sole Proprietorship", "Partnership", "Other"]}
              onChange={handleChange}
            />
          </div>
          <Field
            label="Owner Names (full list)"
            name="owner_names"
            value={form.owner_names}
            onChange={handleChange}
            placeholder="e.g. Joshua Smith, Maria Johnson"
            hint="comma-separated"
          />
        </fieldset>

        {/* Location */}
        <fieldset className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <legend className="text-sm font-semibold text-gray-800 px-1">Location</legend>
          <Field
            label="Street Address"
            name="address"
            value={form.address}
            onChange={handleChange}
            placeholder="e.g. 1234 Mission St"
          />
          <div className="grid grid-cols-3 gap-4">
            <Field
              label="City"
              name="city"
              value={form.city}
              onChange={handleChange}
              placeholder="e.g. Oakland"
              required
            />
            <Field
              label="State"
              name="state"
              value={form.state}
              onChange={handleChange}
              placeholder="California"
            />
            <Field
              label="ZIP"
              name="zip"
              value={form.zip}
              onChange={handleChange}
              placeholder="e.g. 94103"
            />
          </div>
        </fieldset>

        {/* License */}
        <fieldset className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <legend className="text-sm font-semibold text-gray-800 px-1">License</legend>
          <div className="grid grid-cols-3 gap-4">
            <SelectField
              label="License Status"
              name="license_status"
              value={form.license_status}
              options={["Active", "Expired", "Revoked", "Canceled", "Surrendered"]}
              onChange={handleChange}
              required
            />
            <SelectField
              label="License Type"
              name="license_type"
              value={form.license_type}
              options={["Retailer", "Microbusiness", "Distributor", "Other"]}
              onChange={handleChange}
            />
            <SelectField
              label="Designation"
              name="license_designation"
              value={form.license_designation}
              options={["Adult-Use", "Medicinal", "Adult-Use and Medicinal"]}
              onChange={handleChange}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Issue Date"
              name="issue_date"
              value={form.issue_date}
              onChange={handleChange}
              type="date"
            />
            <Field
              label="Expiration Date"
              name="expiration_date"
              value={form.expiration_date}
              onChange={handleChange}
              type="date"
            />
          </div>
          <Field
            label="Activity (microbusiness only)"
            name="activity"
            value={form.activity}
            onChange={handleChange}
            placeholder="e.g. Retail, Distribution"
            hint="leave blank if not applicable"
          />
        </fieldset>

        {/* Contact */}
        <fieldset className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <legend className="text-sm font-semibold text-gray-800 px-1">Contact</legend>
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Business Email"
              name="email"
              value={form.email}
              onChange={handleChange}
              type="email"
              placeholder="hello@dispensary.com"
            />
            <Field
              label="Business Phone"
              name="phone"
              value={form.phone}
              onChange={handleChange}
              placeholder="(510) 555-0100"
            />
          </div>
        </fieldset>

        <div className="flex gap-3">
          <button
            type="submit"
            className="flex-1 py-3 px-6 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm transition-colors"
          >
            Build Prompt
          </button>
          {prompt && (
            <button
              type="button"
              onClick={handleReset}
              className="py-3 px-5 rounded-xl border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 font-medium text-sm transition-colors"
            >
              Reset
            </button>
          )}
        </div>
      </form>

      {prompt && (
        <div id="prompt-output" className="mt-10 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-800">Your Prompt is Ready</h2>
            <CopyButton text={prompt} />
          </div>

          {/* Step instructions */}
          <div className="bg-brand-50 border border-brand-100 rounded-xl p-4 space-y-2">
            <p className="text-sm font-medium text-brand-900">How to use:</p>
            <ol className="text-sm text-brand-800 space-y-1 list-decimal list-inside">
              <li>Click <strong>Copy</strong> above to copy the full prompt.</li>
              <li>Open any free AI chat below and start a new conversation.</li>
              <li>Paste the prompt and send — the AI will generate the full outreach sequence.</li>
            </ol>
          </div>

          {/* AI links */}
          <div className="flex flex-wrap gap-2">
            {AI_LINKS.map(({ label, href, color }) => (
              <a
                key={label}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors ${color}`}
              >
                Open {label}
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            ))}
          </div>

          {/* Prompt preview */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
              <span className="text-xs font-medium text-gray-600">Prompt preview</span>
              <span className="text-xs text-gray-400">{prompt.length.toLocaleString()} characters</span>
            </div>
            <textarea
              readOnly
              value={prompt}
              rows={18}
              className="w-full px-4 py-3 text-xs font-mono text-gray-700 bg-white resize-none focus:outline-none leading-relaxed"
            />
          </div>
        </div>
      )}
    </div>
  );
}
