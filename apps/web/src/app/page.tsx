import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  BarChart3,
  CreditCard,
  FileText,
  Shield,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-primary-foreground font-bold">S</span>
            </div>
            <span className="text-xl font-bold">SimplifyEU</span>
          </div>
          <nav className="hidden md:flex items-center space-x-6">
            <Link href="#features" className="text-muted-foreground hover:text-foreground">
              Features
            </Link>
            <Link href="#pricing" className="text-muted-foreground hover:text-foreground">
              Pricing
            </Link>
            <Link href="/ai-test">
              <Button variant="outline" className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-purple-500/30 hover:border-purple-500">
                <Sparkles className="mr-2 h-4 w-4 text-purple-500" />
                AI Test
              </Button>
            </Link>
            <Link href="/auth/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/auth/register">
              <Button>Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 md:py-32">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
            Simplify Your Business
            <br />
            <span className="text-primary">Management Platform</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
            All-in-one solution for managing your business: invoicing, subscriptions,
            team collaboration, and analytics. Built for European businesses.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/auth/register">
              <Button size="lg" className="w-full sm:w-auto">
                Start Free Trial
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="#features">
              <Button variant="outline" size="lg" className="w-full sm:w-auto">
                Learn More
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-muted/50">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Everything You Need
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              icon={<FileText className="h-10 w-10" />}
              title="Invoicing"
              description="Create and send professional invoices in minutes. Support for multiple currencies and VAT compliance."
            />
            <FeatureCard
              icon={<CreditCard className="h-10 w-10" />}
              title="Subscriptions"
              description="Manage recurring payments and subscriptions with Stripe integration. Automatic billing reminders."
            />
            <FeatureCard
              icon={<Users className="h-10 w-10" />}
              title="Team Collaboration"
              description="Invite team members, assign roles, and manage permissions across your organization."
            />
            <FeatureCard
              icon={<BarChart3 className="h-10 w-10" />}
              title="Analytics"
              description="Real-time insights into your business performance with customizable dashboards."
            />
            <FeatureCard
              icon={<Shield className="h-10 w-10" />}
              title="Security"
              description="Enterprise-grade security with role-based access control and audit logs."
            />
            <FeatureCard
              icon={<Zap className="h-10 w-10" />}
              title="API Access"
              description="Powerful API for integrating with your existing tools and workflows."
            />
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Simple, Transparent Pricing
          </h2>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <PricingCard
              title="Starter"
              price="€29"
              description="Perfect for small businesses"
              features={[
                "Up to 5 team members",
                "100 invoices/month",
                "Basic analytics",
                "Email support",
              ]}
            />
            <PricingCard
              title="Professional"
              price="€79"
              description="For growing businesses"
              features={[
                "Up to 20 team members",
                "Unlimited invoices",
                "Advanced analytics",
                "Priority support",
                "API access",
              ]}
              highlighted
            />
            <PricingCard
              title="Enterprise"
              price="Custom"
              description="For large organizations"
              features={[
                "Unlimited team members",
                "Unlimited invoices",
                "Custom analytics",
                "24/7 support",
                "Custom integrations",
                "SLA guarantee",
              ]}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary text-primary-foreground">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Simplify Your Business?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Start your 14-day free trial today. No credit card required.
          </p>
          <Link href="/auth/register">
            <Button size="lg" variant="secondary">
              Get Started Free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                  <span className="text-primary-foreground font-bold">S</span>
                </div>
                <span className="text-xl font-bold">SimplifyEU</span>
              </div>
              <p className="text-muted-foreground">
                Making business management simple for European companies.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-muted-foreground">
                <li><Link href="#features" className="hover:text-foreground">Features</Link></li>
                <li><Link href="#pricing" className="hover:text-foreground">Pricing</Link></li>
                <li><Link href="#" className="hover:text-foreground">API</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-muted-foreground">
                <li><Link href="#" className="hover:text-foreground">About</Link></li>
                <li><Link href="#" className="hover:text-foreground">Blog</Link></li>
                <li><Link href="#" className="hover:text-foreground">Careers</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-muted-foreground">
                <li><Link href="#" className="hover:text-foreground">Privacy</Link></li>
                <li><Link href="#" className="hover:text-foreground">Terms</Link></li>
                <li><Link href="#" className="hover:text-foreground">Security</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t mt-8 pt-8 text-center text-muted-foreground">
            <p>&copy; {new Date().getFullYear()} SimplifyEU. All rights reserved.</p>
          </div>
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
    <div className="p-6 bg-card rounded-lg border shadow-sm">
      <div className="text-primary mb-4">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}

function PricingCard({
  title,
  price,
  description,
  features,
  highlighted = false,
}: {
  title: string;
  price: string;
  description: string;
  features: string[];
  highlighted?: boolean;
}) {
  return (
    <div
      className={`p-6 rounded-lg border ${
        highlighted
          ? "border-primary bg-card shadow-lg scale-105"
          : "bg-card"
      }`}
    >
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <div className="text-4xl font-bold mb-2">
        {price}
        <span className="text-md font-normal text-muted-foreground">/month</span>
      </div>
      <p className="text-muted-foreground mb-6">{description}</p>
      <ul className="space-y-3 mb-6">
        {features.map((feature, index) => (
          <li key={index} className="flex items-center text-sm">
            <svg
              className="mr-2 h-4 w-4 text-primary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            {feature}
          </li>
        ))}
      </ul>
      <Link href="/auth/register" className="block">
        <Button className="w-full" variant={highlighted ? "default" : "outline"}>
          Get Started
        </Button>
      </Link>
    </div>
  );
}