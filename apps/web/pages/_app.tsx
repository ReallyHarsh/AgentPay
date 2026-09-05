import '@/styles/globals.css';
import type { AppProps } from 'next/app';
import Head from 'next/head';
import { FloatingNav } from '@/components/FloatingNav';
import { ThemeProvider } from '@/lib/ThemeContext';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ThemeProvider>
      <Head>
        <title>AgentPay — Autonomous Shopping with Visible Financial Control</title>
        <meta
          name="description"
          content="Autonomous AI commerce with deterministic financial guardrails and visible Razorpay settlement."
        />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen text-[#1B1C1C] dark:text-[#F5F3F3] flex flex-col relative selection:bg-[#FE7352]/20 selection:text-[#AA361A] transition-colors duration-200">
        {/* Floating Top Navigation */}
        <FloatingNav />

        {/* Main Content Viewport */}
        <main className="flex-1 w-full pt-16 sm:pt-20 pb-16 px-4 sm:px-6 md:px-8 max-w-5xl mx-auto flex flex-col">
          <Component {...pageProps} />
        </main>
      </div>
    </ThemeProvider>
  );
}
