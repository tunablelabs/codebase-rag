import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 sticky bottom-0">
      <div className="mx-auto max-w-5xl px-4 py-2 text-sm text-slate-600 dark:text-slate-400">
        Powered by{" "}
        <Link
          className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
          target="_blank"
          href="https://www.tunablelabs.ai/"
        >
          TunableLabs
        </Link>
      </div>
    </footer>
  );
}