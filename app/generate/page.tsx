import OutreachForm from "@/app/components/OutreachForm";
import Link from "next/link";

export const metadata = {
  title: "Paytree — Outreach Generator",
};

export default function GeneratePage() {
  return (
    <>
      <div className="border-b border-gray-200 bg-white px-6 py-3 flex items-center gap-4">
        <Link href="/" className="text-sm text-gray-500 hover:text-gray-800 transition-colors">
          ← Back to Paytree
        </Link>
      </div>
      <OutreachForm />
    </>
  );
}
