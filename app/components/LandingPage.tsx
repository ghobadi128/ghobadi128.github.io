"use client";
import { useState } from "react";
import Link from "next/link";

const ATM_OPTIONS = [
  "We don't have an ATM",
  "We have one but it's old / unreliable",
  "We have one but we don't earn from it",
  "We have one — it's working fine",
  "We use a third-party ATM provider",
];

function NavBar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/90 backdrop-blur border-b border-white/10">
      <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
        <span className="text-white font-bold text-lg tracking-tight">Paytree</span>
        <div className="flex items-center gap-6">
          <a href="#how-it-works" className="text-sm text-white/60 hover:text-white transition-colors hidden sm:block">
            How it works
          </a>
          <a href="#problems" className="text-sm text-white/60 hover:text-white transition-colors hidden sm:block">
            Common problems
          </a>
          <a
            href="#signup"
            className="text-sm font-semibold bg-green-500 hover:bg-green-400 text-black px-4 py-1.5 rounded-full transition-colors"
          >
            Get started
          </a>
        </div>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section className="bg-black pt-14 min-h-screen flex items-center">
      <div className="max-w-5xl mx-auto px-6 py-24 sm:py-32">
        <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-full px-4 py-1 mb-8">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-green-400 text-xs font-semibold tracking-wide uppercase">
            Zero upfront cost · Fully managed · You keep 70–75%
          </span>
        </div>

        <h1 className="text-5xl sm:text-7xl font-extrabold text-white leading-[1.05] tracking-tight mb-6">
          Your dispensary
          <br />
          should be{" "}
          <span className="text-green-400">making money</span>
          <br />
          while you sleep.
        </h1>

        <p className="text-xl sm:text-2xl text-white/60 max-w-2xl leading-relaxed mb-10">
          Paytree places a fully managed ATM inside your dispensary at{" "}
          <strong className="text-white">no cost to you</strong>. Every transaction earns you
          passive surcharge revenue — deposited monthly, no effort required.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-16">
          <a
            href="#signup"
            className="inline-flex items-center justify-center gap-2 bg-green-500 hover:bg-green-400 text-black font-bold text-lg px-8 py-4 rounded-xl transition-colors"
          >
            Claim your free ATM placement
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </a>
          <a
            href="#how-it-works"
            className="inline-flex items-center justify-center gap-2 border border-white/20 text-white hover:bg-white/5 font-medium text-lg px-8 py-4 rounded-xl transition-colors"
          >
            See how it works
          </a>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/10 rounded-2xl overflow-hidden">
          {[
            { value: "$900–$4K", label: "Monthly passive income" },
            { value: "70–75%", label: "Surcharge revenue, yours" },
            { value: "$0", label: "Upfront cost, ever" },
            { value: "20 yrs", label: "ISO-certified experience" },
          ].map(({ value, label }) => (
            <div key={label} className="bg-white/5 px-6 py-5">
              <div className="text-2xl sm:text-3xl font-extrabold text-green-400">{value}</div>
              <div className="text-xs text-white/50 mt-1 leading-snug">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      n: "01",
      title: "We install — free",
      body: "We place a fully managed, NFC-ready ATM (Apple Pay, Google Pay, tap-to-pay) inside your dispensary. Hardware, installation, setup: all on us.",
    },
    {
      n: "02",
      title: "We handle everything",
      body: "Cash loading, maintenance, uptime monitoring, compliance — all handled by our team. You don't lift a finger. Downtime is our problem, not yours.",
    },
    {
      n: "03",
      title: "You earn every month",
      body: "You keep 70–75% of every surcharge transaction from foot traffic you already have. Monthly deposit, no overhead, no surprises.",
    },
  ];

  return (
    <section id="how-it-works" className="bg-gray-950 py-24">
      <div className="max-w-5xl mx-auto px-6">
        <div className="mb-14">
          <h2 className="text-4xl sm:text-5xl font-extrabold text-white mb-4">
            Three steps. No catch.
          </h2>
          <p className="text-white/50 text-lg max-w-xl">
            We've done this for 20 years. The setup is faster than you think.
          </p>
        </div>

        <div className="grid sm:grid-cols-3 gap-6">
          {steps.map(({ n, title, body }) => (
            <div key={n} className="bg-white/5 border border-white/10 rounded-2xl p-7">
              <div className="text-5xl font-black text-green-500/30 mb-4 leading-none">{n}</div>
              <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
              <p className="text-sm text-white/50 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Problems() {
  const issues = [
    {
      headline: "Getting dropped by your processor",
      detail:
        "Banks and processors regularly exit the cannabis space with little notice. If your payment setup depends on one provider and they leave, you're stuck — often mid-month.",
    },
    {
      headline: "ATM hardware that's past its prime",
      detail:
        "Dispensaries that opened in 2019–2021 are hitting the five-year wall right now. Old ATMs fail more often, especially under high transaction volume, and downtime directly costs you customers.",
    },
    {
      headline: "ATM income going to someone else",
      detail:
        "Most dispensary ATMs are owned by a third party who keeps the majority of surcharge revenue. If you don't know what your ATM earns per month, you're probably not getting your share.",
    },
    {
      headline: "Cash customers leaving empty-handed",
      detail:
        "An ATM that's down during peak hours is a sale lost. In a cash-heavy industry, a failed ATM doesn't just inconvenience customers — it sends them to the dispensary down the street.",
    },
    {
      headline: "NFC not working as a fallback",
      detail:
        "Apple Pay, Google Pay, and tap-to-pay reduce dependence on cash — but only if they're properly configured. Many dispensaries have NFC hardware that was never set up correctly.",
    },
  ];

  return (
    <section id="problems" className="bg-black py-24 border-t border-white/10">
      <div className="max-w-5xl mx-auto px-6">
        <div className="mb-14">
          <h2 className="text-4xl sm:text-5xl font-extrabold text-white mb-4">
            Sound familiar?
          </h2>
          <p className="text-white/40 text-base">
            These are the most common payment infrastructure problems we see in dispensaries across California. Most operators don't know it's happening until it's already a problem.
          </p>
        </div>

        <div className="space-y-px rounded-2xl overflow-hidden border border-white/10">
          {issues.map(({ headline, detail }) => (
            <details
              key={headline}
              className="group bg-white/5 hover:bg-white/[0.07] transition-colors"
            >
              <summary className="flex items-center justify-between px-6 py-5 cursor-pointer list-none">
                <span className="font-semibold text-white text-base">{headline}</span>
                <svg
                  className="w-4 h-4 text-white/40 group-open:rotate-45 transition-transform flex-shrink-0 ml-4"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
              </summary>
              <p className="px-6 pb-5 text-sm text-white/50 leading-relaxed max-w-2xl">{detail}</p>
            </details>
          ))}
        </div>

        <p className="mt-8 text-sm text-white/30 text-center">
          Already working with us and experiencing one of these? Scroll down and let us know.
        </p>
      </div>
    </section>
  );
}

function SignupForm() {
  const [form, setForm] = useState({
    name: "",
    dispensary: "",
    email: "",
    phone: "",
    atm_situation: "",
    pain_point: "",
  });
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const set = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");
    try {
      const res = await fetch("/api/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Submission failed");
      setStatus("success");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong");
      setStatus("error");
    }
  };

  const inputCls =
    "w-full px-4 py-3 bg-white/5 border border-white/15 rounded-xl text-white text-sm placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition";

  const labelCls = "block text-xs font-semibold text-white/50 uppercase tracking-wide mb-1.5";

  if (status === "success") {
    return (
      <section id="signup" className="bg-gray-950 py-24 border-t border-white/10">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-3xl font-extrabold text-white mb-3">You're on our list.</h2>
          <p className="text-white/50 text-lg mb-2">
            Someone from Paytree will reach out within one business day.
          </p>
          <p className="text-white/30 text-sm">
            Questions? Email us at{" "}
            <a href="mailto:dev@paytree.com" className="text-green-400 hover:underline">
              dev@paytree.com
            </a>
          </p>
        </div>
      </section>
    );
  }

  return (
    <section id="signup" className="bg-gray-950 py-24 border-t border-white/10">
      <div className="max-w-2xl mx-auto px-6">
        <div className="mb-10">
          <h2 className="text-4xl sm:text-5xl font-extrabold text-white mb-4">
            Let's get you set up.
          </h2>
          <p className="text-white/50 text-lg leading-relaxed">
            Tell us who you are and what you're dealing with. We already know the dispensary landscape — we just need to know where you stand so we can come in with the right answer, not a generic pitch.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid sm:grid-cols-2 gap-5">
            <div>
              <label className={labelCls}>Your name</label>
              <input
                className={inputCls}
                placeholder="First name is fine"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
              />
            </div>
            <div>
              <label className={labelCls}>
                Dispensary name <span className="text-green-400">*</span>
              </label>
              <input
                className={inputCls}
                placeholder="DBA or legal name"
                required
                value={form.dispensary}
                onChange={(e) => set("dispensary", e.target.value)}
              />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-5">
            <div>
              <label className={labelCls}>
                Email <span className="text-green-400">*</span>
              </label>
              <input
                type="email"
                className={inputCls}
                placeholder="you@dispensary.com"
                required
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
              />
            </div>
            <div>
              <label className={labelCls}>Phone</label>
              <input
                type="tel"
                className={inputCls}
                placeholder="(510) 555-0100"
                value={form.phone}
                onChange={(e) => set("phone", e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className={labelCls}>Your current ATM situation</label>
            <select
              className={`${inputCls} cursor-pointer`}
              value={form.atm_situation}
              onChange={(e) => set("atm_situation", e.target.value)}
            >
              <option value="">Select one…</option>
              {ATM_OPTIONS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelCls}>
              Any payment processor or ATM problems you're dealing with?
            </label>
            <textarea
              className={`${inputCls} resize-none`}
              rows={4}
              placeholder="Tell us what's going on — processor dropping you, ATM downtime, not earning what you expected, anything. The more specific, the better we can help."
              value={form.pain_point}
              onChange={(e) => set("pain_point", e.target.value)}
            />
          </div>

          {status === "error" && (
            <p className="text-sm text-red-400">{errorMsg}</p>
          )}

          <button
            type="submit"
            disabled={status === "loading"}
            className="w-full py-4 bg-green-500 hover:bg-green-400 disabled:opacity-50 text-black font-bold text-lg rounded-xl transition-colors"
          >
            {status === "loading" ? "Sending…" : "Get my free ATM placement →"}
          </button>

          <p className="text-xs text-white/25 text-center">
            No spam. No sales deck. Someone from our team will follow up within one business day.
          </p>
        </form>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="bg-black border-t border-white/10 py-10">
      <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <span className="text-white/30 text-sm">
          © {new Date().getFullYear()} Paytree · ISO-certified payment infrastructure
        </span>
        <div className="flex items-center gap-6 text-sm text-white/30">
          <a href="mailto:dev@paytree.com" className="hover:text-white/60 transition-colors">
            dev@paytree.com
          </a>
          <Link href="/generate" className="hover:text-white/60 transition-colors">
            Outreach generator
          </Link>
        </div>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className="bg-black">
      <NavBar />
      <Hero />
      <HowItWorks />
      <Problems />
      <SignupForm />
      <Footer />
    </div>
  );
}
