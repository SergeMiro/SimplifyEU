# SimplifyEU

## Overview
SimplifyEU is an AI-powered business management platform designed specifically for companies operating within the European Union. Our mission is to simplify administrative overhead through automation and intelligent insights while ensuring full compliance with EU regulations (VAT, GDPR, etc.).

## Key Features
- **Smart Invoicing**: Generate EU-compliant multi-currency invoices with automatic VAT calculation.
- **Subscription Management**: Automated billing and recurring payment tracking.
- **AI Analytics**: Intelligent business performance monitoring and predictions.
- **Team Collaboration**: Role-based access and seamless organizational management.

## Tech Stack & Integrations
- **Framework**: [Next.js](https://nextjs.org/) (App Router)
- **Database & Auth**: [Supabase](https://supabase.com/)
- **Payments**: [Stripe](https://stripe.com/)
- **AI Engine**: [OpenAI](https://openai.com/)
- **Hosting**: [Vercel](https://vercel.com/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + [Radix UI](https://www.radix-ui.com/)

## Getting Started

### Local Development
1. Install dependencies:
   ```bash
   pnpm install
   ```
2. Run development server:
   ```bash
   pnpm run dev
   ```
3. Open [http://localhost:3000](http://localhost:3000)

## Mobile-First Design
The platform features a modern, responsive design optimized for mobile devices, including a dedicated bottom navigation bar for quick access on small screens and a refined, touch-friendly UI.

## Testing
- **UI/UX**: Check responsiveness using browser developer tools (Mobile view).
- **AI Features**: Navigate to `/ai-test` to verify AI model integrations.
- **Auth**: Use the `/auth/login` and `/auth/register` flows powered by Supabase.
