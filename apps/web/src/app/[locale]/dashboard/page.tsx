"use client";

import { Link } from "@/i18n/routing";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  CreditCard, 
  FileSearch, 
  Sparkles, 
  ArrowRight, 
  BarChart3,
  Shield
} from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-50 via-background to-background dark:from-purple-950/10">
      {/* Header */}
      <header className="border-b bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-pink-500 rounded-lg flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-sm">S</span>
            </div>
            <span className="text-xl font-bold">SimplifyEU</span>
          </div>
          <nav className="flex items-center space-x-4">
            <Link href="/">
              <Button variant="ghost" size="sm">Home</Button>
            </Link>
            <Link href="/ai-test">
              <Button variant="outline" size="sm" className="border-purple-200">
                <Sparkles className="mr-2 h-4 w-4 text-purple-500" />
                AI Lab
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-12 max-w-6xl">
        {/* Welcome */}
        <div className="mb-12">
          <h1 className="text-4xl font-extrabold tracking-tight mb-2">
            Welcome to your <span className="text-purple-600">Dashboard</span>
          </h1>
          <p className="text-md text-muted-foreground">
            Manage your finances, detect hidden subscriptions, and leverage AI insights.
          </p>
        </div>

        {/* Services Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Subscription Detector */}
          <Link href="/dashboard/services/subscription-detector" className="group">
            <Card className="h-full border-purple-100 dark:border-purple-900/30 hover:border-purple-300 dark:hover:border-purple-700 hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-pink-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
              <CardHeader>
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-4 shadow-lg shadow-purple-500/20">
                  <FileSearch className="h-6 w-6 text-white" />
                </div>
                <CardTitle className="flex items-center justify-between">
                  Subscription Detector
                  <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-purple-500 group-hover:translate-x-1 transition-all" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Upload your bank statement and let AI find hidden subscriptions you might have forgotten about.
                </p>
                <div className="mt-4 flex items-center gap-2 text-sm text-purple-600 font-medium">
                  <Sparkles className="h-4 w-4" />
                  AI-Powered
                </div>
              </CardContent>
            </Card>
          </Link>

          {/* AI Test Lab */}
          <Link href="/ai-test" className="group">
            <Card className="h-full border-purple-100 dark:border-purple-900/30 hover:border-purple-300 dark:hover:border-purple-700 hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-pink-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
              <CardHeader>
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/20">
                  <Sparkles className="h-6 w-6 text-white" />
                </div>
                <CardTitle className="flex items-center justify-between">
                  AI Lab
                  <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-purple-500 group-hover:translate-x-1 transition-all" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Test our AI capabilities with streaming responses. Chat with Mistral-3.1 powered by Chutes AI.
                </p>
                <div className="mt-4 flex items-center gap-2 text-sm text-indigo-600 font-medium">
                  <CreditCard className="h-4 w-4" />
                  Real-time Streaming
                </div>
              </CardContent>
            </Card>
          </Link>

          {/* Analytics (Coming Soon) */}
          <Card className="h-full border-gray-200 dark:border-gray-800 opacity-60 relative overflow-hidden">
            <div className="absolute top-4 right-4 px-2 py-1 bg-muted text-muted-foreground text-xs rounded-full font-medium">
              Coming Soon
            </div>
            <CardHeader>
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center mb-4">
                <BarChart3 className="h-6 w-6 text-white" />
              </div>
              <CardTitle>Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Visualize your spending patterns and get insights into your financial health.
              </p>
            </CardContent>
          </Card>

          {/* Security (Coming Soon) */}
          <Card className="h-full border-gray-200 dark:border-gray-800 opacity-60 relative overflow-hidden">
            <div className="absolute top-4 right-4 px-2 py-1 bg-muted text-muted-foreground text-xs rounded-full font-medium">
              Coming Soon
            </div>
            <CardHeader>
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center mb-4">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <CardTitle>Security Audit</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Review your account access and permissions. Keep your data safe.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Stats (placeholder) */}
        <div className="mt-12 p-8 rounded-3xl border bg-card/50 backdrop-blur-sm">
          <h2 className="text-xl font-bold mb-6">Quick Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-3xl font-extrabold text-purple-600">0</div>
              <div className="text-sm text-muted-foreground">Analyses Run</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-extrabold text-pink-600">€0</div>
              <div className="text-sm text-muted-foreground">Potential Savings</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-extrabold text-indigo-600">0</div>
              <div className="text-sm text-muted-foreground">Subscriptions Found</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-extrabold text-blue-600">0</div>
              <div className="text-sm text-muted-foreground">AI Queries</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
