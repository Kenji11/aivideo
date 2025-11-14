import { ArrowLeft, Check, Zap, Crown, Infinity } from 'lucide-react';
import { useState } from 'react';

interface BillingProps {
  onBack: () => void;
}

const plans = [
  {
    id: 'free',
    name: 'Free',
    icon: Zap,
    price: 0,
    period: 'forever',
    description: 'Get started creating',
    features: [
      '10 videos per month',
      '1GB storage',
      'Basic templates',
      'Community support',
      '720p export',
    ],
    cta: 'Current Plan',
    highlighted: false,
  },
  {
    id: 'pro',
    name: 'Professional',
    icon: Crown,
    price: 29,
    period: 'month',
    description: 'Most popular for creators',
    features: [
      '100 videos per month',
      '500GB storage',
      'All templates',
      'Email support',
      '4K export',
      'Custom branding',
      'Team collaboration (3 members)',
    ],
    cta: 'Upgrade to Pro',
    highlighted: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    icon: Infinity,
    price: 99,
    period: 'month',
    description: 'For teams and agencies',
    features: [
      'Unlimited videos',
      'Unlimited storage',
      'Priority support',
      '8K export',
      'White label',
      'Advanced analytics',
      'Unlimited team members',
      'API access',
      'Custom workflows',
    ],
    cta: 'Contact Sales',
    highlighted: false,
  },
];

export function Billing({ onBack }: BillingProps) {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 text-slate-600 hover:text-slate-900 mb-6 transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back</span>
      </button>

      <div className="mb-12">
        <h1 className="text-3xl font-bold text-slate-900">Billing & Plans</h1>
        <p className="text-slate-600 mt-1">Choose the perfect plan for your needs</p>
      </div>

      <div className="flex items-center justify-center space-x-6 mb-12">
        <button
          onClick={() => setBillingCycle('monthly')}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            billingCycle === 'monthly'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          Monthly
        </button>
        <button
          onClick={() => setBillingCycle('yearly')}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            billingCycle === 'yearly'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          Yearly <span className="text-xs ml-2">Save 20%</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {plans.map((plan) => {
          const Icon = plan.icon;
          const yearlyPrice = plan.price === 0 ? 0 : Math.floor(plan.price * 12 * 0.8);
          const displayPrice = billingCycle === 'yearly' ? yearlyPrice : plan.price;

          return (
            <div
              key={plan.id}
              className={`card overflow-hidden transition-all hover:shadow-lg ${
                plan.highlighted ? 'ring-2 ring-blue-600 transform lg:scale-105' : ''
              }`}
            >
              <div className={`p-6 ${plan.highlighted ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white' : 'bg-slate-50'}`}>
                <div className="flex items-center space-x-3 mb-2">
                  <Icon className="w-8 h-8" />
                  <h3 className="text-2xl font-bold">{plan.name}</h3>
                </div>
                <p className={`text-sm ${plan.highlighted ? 'text-blue-100' : 'text-slate-600'}`}>
                  {plan.description}
                </p>
              </div>

              <div className="p-6 space-y-6">
                <div>
                  {plan.price === 0 ? (
                    <p className="text-4xl font-bold text-slate-900">Free</p>
                  ) : (
                    <>
                      <div className="flex items-baseline space-x-2">
                        <span className="text-4xl font-bold text-slate-900">${displayPrice}</span>
                        <span className="text-slate-600">/{billingCycle === 'yearly' ? 'year' : 'month'}</span>
                      </div>
                      {billingCycle === 'yearly' && plan.price > 0 && (
                        <p className="text-xs text-green-600 mt-2">Save ${(plan.price * 12 - displayPrice).toFixed(0)}/year</p>
                      )}
                    </>
                  )}
                </div>

                <button
                  className={`w-full py-3 px-4 rounded-lg font-medium transition-all ${
                    plan.id === 'pro'
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'border-2 border-slate-300 text-slate-900 hover:border-blue-600 hover:text-blue-600'
                  }`}
                >
                  {plan.cta}
                </button>

                <div className="space-y-3">
                  {plan.features.map((feature, idx) => (
                    <div key={idx} className="flex items-start space-x-3">
                      <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-slate-700">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-16 card p-8">
        <h3 className="text-xl font-bold text-slate-900 mb-4">Frequently Asked Questions</h3>
        <div className="space-y-4">
          {[
            {
              q: 'Can I change plans anytime?',
              a: 'Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately.',
            },
            {
              q: 'What payment methods do you accept?',
              a: 'We accept all major credit cards, PayPal, and bank transfers for enterprise plans.',
            },
            {
              q: 'Is there a free trial?',
              a: 'Yes! Our Free plan is permanent with 10 videos per month. Pro and Enterprise plans have 14-day trials.',
            },
            {
              q: 'What if I go over my monthly limit?',
              a: 'We\'ll notify you before reaching your limit. You can either upgrade or wait for your monthly reset.',
            },
          ].map((faq, idx) => (
            <div key={idx} className="border-b border-slate-200 pb-4 last:border-b-0">
              <p className="font-medium text-slate-900 mb-2">{faq.q}</p>
              <p className="text-slate-600">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
