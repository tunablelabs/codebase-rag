import Link from "next/link";

export default function Footer() {
  return (
    <footer className="sticky bottom-0 border-t border-sky-200/20 bg-base-100/95 backdrop-blur-sm">
      <div className="mx-auto max-w-5xl px-4 py-2 flex justify-end items-center">
        <span className="text-sm text-slate-600 dark:text-slate-400">
          Powered by{" "}
          <Link
            className="ml-1 font-medium text-blue-600 dark:text-blue-400 hover:underline"
            target="_blank"
            href="https://www.tunablelabs.ai/"
          >
            TunableLabs
          </Link>
        </span>
      </div>
    </footer>
  );
}