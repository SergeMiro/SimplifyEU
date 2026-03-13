import { Link } from '@/i18n/routing';
import { useTranslations } from 'next-intl';
import LanguageSwitcher from '@/components/language-switcher';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import {
  ArrowRight,
  BarChart3,
  CreditCard,
  FileText,
  Shield,
  Sparkles,
  Users,
  Zap,
  Menu,
  Database,
  Cloud,
  BrainCircuit
} from 'lucide-react';

export default function Home() {
  const t = useTranslations('HomePage');
  const tNav = useTranslations('Navigation');
  const tAuth = useTranslations('Auth');

  return (
    <div className="min-h-screen bg-background flex flex-col pb-16 md:pb-0">
      {/* Mobile-first Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-primary-foreground font-bold">S</span>
            </div>
            <span className="text-xl font-bold tracking-tight">SimplifyEU</span>
          </div>
          
          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <Link href="#features" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Features
            </Link>
            <Link href="#integrations" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Integrations
            </Link>
            <LanguageSwitcher />
            <ThemeToggle />
            <Link href="/auth/login">
              <Button variant="ghost" size="sm">{tAuth('signIn')}</Button>
            </Link>
            <Link href="/auth/register">
              <Button size="sm">Get Started</Button>
            </Link>
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex items-center md:hidden gap-2">
            <LanguageSwitcher />
            <ThemeToggle />
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section - Mobile Optimized */}
        <section className="px-4 py-12 md:py-24 lg:py-32">
          <div className="container mx-auto text-center flex flex-col items-center">
            <div className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80 mb-6">
              AI-Powered Management Platform
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight mb-4 max-w-3xl">
              {t('title') || 'Simplify Your Business'}
              <br className="hidden sm:inline" />
              <span className="text-primary block mt-2">in the European Union</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-[42rem] mx-auto mb-8 leading-normal sm:leading-8">
              SimplifyEU is an all-in-one AI-driven service designed specifically for EU businesses. We provide seamless invoicing, subscription management, team collaboration, and powerful analytics, fully compliant with EU regulations.
            </p>
            <div className="flex flex-col w-full sm:w-auto sm:flex-row items-center gap-3">
              <Link href="/auth/register" className="w-full sm:w-auto">
                <Button size="lg" className="w-full h-12 px-8">
                  Start Free Trial
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/ai-test" className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="outline"
                  className="w-full h-12 px-8 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-purple-500/30 hover:border-purple-500"
                >
                  <Sparkles className="mr-2 h-4 w-4 text-purple-500" />
                  Try AI Test
                </Button>
              </Link>
            </div>
          </div>
        </section>

        {/* Integrated Services Section */}
        <section id="integrations" className="py-12 md:py-24 bg-muted/40">
          <div className="container mx-auto px-4">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold tracking-tight mb-4">Powerful Integrations</h2>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                Built on top of industry-leading services to ensure reliability, security, and performance.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <FeatureCard
                icon={<Database className="h-8 w-8 text-emerald-500" />}
                title="Supabase"
                description="PostgreSQL database, real-time subscriptions, and secure authentication for your data."
              />
              <FeatureCard
                icon={<CreditCard className="h-8 w-8 text-indigo-500" />}
                title="Stripe"
                description="Secure payment processing, invoicing, and automated subscription management."
              />
              <FeatureCard
                icon={<Cloud className="h-8 w-8 text-slate-900 dark:text-slate-100" />}
                title="Vercel"
                description="Lightning-fast edge global deployment and hosting for seamless user experience."
              />
              <FeatureCard
                icon={<BrainCircuit className="h-8 w-8 text-purple-500" />}
                title="OpenAI"
                description="Advanced AI models powering our smart analytics and automated business insights."
              />
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-12 md:py-24">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-center mb-10 tracking-tight">
              Core Capabilities
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <FeatureCard
                icon={<FileText className="h-8 w-8" />}
                title="Smart Invoicing"
                description="Create and send professional invoices in minutes. Support for multiple currencies and VAT compliance."
              />
              <FeatureCard
                icon={<Users className="h-8 w-8" />}
                title="Team Collaboration"
                description="Invite team members, assign roles, and manage permissions across your organization."
              />
              <FeatureCard
                icon={<BarChart3 className="h-8 w-8" />}
                title="Analytics"
                description="Real-time insights into your business performance with customizable dashboards."
              />
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16 md:py-24 bg-primary text-primary-foreground">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight">
              Ready to Simplify Your Business?
            </h2>
            <p className="text-lg mb-8 opacity-90 max-w-xl mx-auto">
              Start your 14-day free trial today. No credit card required.
            </p>
            <Link href="/auth/register">
              <Button size="lg" variant="secondary" className="w-full sm:w-auto h-12 px-8">
                Get Started Free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </section>
      </main>

      {/* Mobile Bottom Navigation */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 p-2 z-50 flex justify-around items-center">
        <Link href="/" className="flex flex-col items-center p-2 text-primary">
          <BarChart3 className="h-5 w-5" />
          <span className="text-[10px] mt-1 font-medium">Home</span>
        </Link>
        <Link href="/ai-test" className="flex flex-col items-center p-2 text-muted-foreground hover:text-primary transition-colors">
          <Sparkles className="h-5 w-5" />
          <span className="text-[10px] mt-1 font-medium">AI Test</span>
        </Link>
        <ThemeToggle />
        <Link href="/auth/login" className="flex flex-col items-center p-2 text-muted-foreground hover:text-primary transition-colors">
          <Users className="h-5 w-5" />
          <span className="text-[10px] mt-1 font-medium">Account</span>
        </Link>
      </div>

      {/* Footer */}
      <footer className="border-t py-8 md:py-12 bg-muted/20">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} SimplifyEU. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 bg-card rounded-xl border shadow-sm hover:shadow-md transition-shadow">
      <div className="text-primary mb-4 p-3 bg-primary/10 inline-flex rounded-lg">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}
