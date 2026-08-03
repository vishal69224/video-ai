import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Clapperboard,
  ImagePlus,
  Layers3,
  Play,
  ShieldCheck,
  Sparkles,
  Timer,
  WandSparkles,
  Zap,
} from 'lucide-react'
import { HeroGallery } from '@/components/HeroGallery'
import { PrimaryButton } from '@/components/PrimaryButton'
import { SectionTitle } from '@/components/SectionTitle'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

const FEATURES = [
  {
    icon: ImagePlus,
    title: 'Multi-image understanding',
    description:
      'Upload up to ten product references so Lumina can capture form, material, and brand detail.',
  },
  {
    icon: WandSparkles,
    title: 'Automatic cinematic prompts',
    description:
      'AI turns your stills into motion direction with lighting, camera language, and pacing.',
  },
  {
    icon: Clapperboard,
    title: 'Studio-ready outputs',
    description:
      'Generate polished product videos ready for social, ads, and launch campaigns.',
  },
]

const STEPS = [
  {
    icon: ImagePlus,
    title: 'Upload Images',
    description: 'Drop product photos into a clean uploader built for speed and clarity.',
  },
  {
    icon: Layers3,
    title: 'AI Understands Images',
    description: 'Lumina analyzes silhouette, texture, color, and composition cues.',
  },
  {
    icon: Sparkles,
    title: 'AI Generates Prompt',
    description: 'A cinematic prompt is crafted automatically from your references.',
  },
  {
    icon: Clapperboard,
    title: 'Video Generated',
    description: 'Watch the progress timeline finish, then open your new video in the library.',
  },
]

const BENEFITS = [
  {
    icon: Zap,
    title: 'Ship creative faster',
    description: 'Go from still product photography to motion content without a full production crew.',
  },
  {
    icon: Timer,
    title: 'Keep the workflow simple',
    description: 'One elegant flow for upload, generation, and library management.',
  },
  {
    icon: ShieldCheck,
    title: 'Premium brand feel',
    description: 'A restrained interface designed for teams who care about polish and craft.',
  },
]

const FAQS = [
  {
    q: 'How many images can I upload?',
    a: 'You can upload between 1 and 10 images in PNG, JPG, JPEG, or WEBP. More references generally improve consistency and quality.',
  },
  {
    q: 'Do I need to write prompts myself?',
    a: 'No. Lumina analyzes your images and generates a cinematic prompt automatically as part of the generation timeline.',
  },
  {
    q: 'Is this connected to a real video API?',
    a: 'Yes. Lumina uploads your images to the backend, generates a cinematic prompt, submits an Image-to-Video job, and polls live status until your MP4 is ready.',
  },
  {
    q: 'Can I cancel a generation?',
    a: 'Yes. On the progress screen you can leave at any time and return to the generator, or open the library to check finished videos later.',
  },
]

const fadeUp = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.3 },
  transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
}

export function LandingPage() {
  return (
    <div>
      <section className="relative overflow-hidden">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10 lg:px-8 lg:py-24">
          <motion.div
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-line bg-white/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-accent shadow-soft">
              <Sparkles className="h-3.5 w-3.5" />
              Lumina Studio
            </p>
            <h1 className="font-display text-4xl font-semibold tracking-tight text-ink text-balance sm:text-5xl lg:text-[3.5rem] lg:leading-[1.05]">
              Create Cinematic AI Videos From Images
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-mute sm:text-lg">
              Upload one or multiple product images and generate professional AI videos
              automatically.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <PrimaryButton asChild size="lg" variant="accent">
                <Link to="/generate">
                  Generate Video
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </PrimaryButton>
              <PrimaryButton asChild size="lg" variant="secondary">
                <a href="#how-it-works">
                  <Play className="h-4 w-4" />
                  View Demo
                </a>
              </PrimaryButton>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="w-full min-w-0 self-stretch lg:pl-2"
          >
            <HeroGallery />
          </motion.div>
        </div>
      </section>

      <section className="border-y border-line/70 bg-white/50 py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <SectionTitle
            eyebrow="Capabilities"
            title="Built for elegant product storytelling"
            description="Everything in the interface is designed to feel calm, fast, and intentionally premium."
          />
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {FEATURES.map((feature, index) => (
              <motion.article
                key={feature.title}
                {...fadeUp}
                transition={{ ...fadeUp.transition, delay: index * 0.08 }}
                whileHover={{ y: -4 }}
                className="rounded-2xl border border-line bg-white p-6 shadow-soft"
              >
                <span className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <feature.icon className="h-5 w-5" />
                </span>
                <h3 className="font-display text-lg font-semibold tracking-tight text-ink">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-mute">{feature.description}</p>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="scroll-mt-24 py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <SectionTitle
            eyebrow="How it works"
            title="From stills to motion in four steps"
            description="A clear pipeline that keeps creative teams focused on the outcome, not the tooling."
          />
          <div className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {STEPS.map((step, index) => (
              <motion.article
                key={step.title}
                {...fadeUp}
                transition={{ ...fadeUp.transition, delay: index * 0.07 }}
                className="relative rounded-2xl border border-line bg-white/80 p-6 shadow-soft"
              >
                <span className="mb-4 inline-flex h-8 w-8 items-center justify-center rounded-full bg-ink text-xs font-semibold text-white">
                  {index + 1}
                </span>
                <span className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-canvas text-ink">
                  <step.icon className="h-5 w-5" />
                </span>
                <h3 className="font-display text-lg font-semibold tracking-tight">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-mute">{step.description}</p>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-line/70 bg-ink py-20 text-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <SectionTitle
            eyebrow="Benefits"
            title="A quieter way to produce standout video"
            description="Less busywork. More cinematic output. A workflow that feels as refined as the content it creates."
            className="[&_h2]:text-white [&_p]:text-white/65 [&_p.text-xs]:text-teal-200"
          />
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {BENEFITS.map((benefit, index) => (
              <motion.article
                key={benefit.title}
                {...fadeUp}
                transition={{ ...fadeUp.transition, delay: index * 0.08 }}
                className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur"
              >
                <span className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-white/10 text-teal-200">
                  <benefit.icon className="h-5 w-5" />
                </span>
                <h3 className="font-display text-lg font-semibold tracking-tight">{benefit.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-white/65">{benefit.description}</p>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      <section id="faq" className="scroll-mt-24 py-20">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <SectionTitle
            eyebrow="FAQ"
            title="Questions, answered clearly"
            description="Everything you need to know about this frontend-only Lumina experience."
          />
          <motion.div
            {...fadeUp}
            className="mt-10 rounded-2xl border border-line bg-white px-5 shadow-soft sm:px-6"
          >
            <Accordion type="single" collapsible className="w-full">
              {FAQS.map((item, index) => (
                <AccordionItem key={item.q} value={`item-${index}`}>
                  <AccordionTrigger>{item.q}</AccordionTrigger>
                  <AccordionContent>{item.a}</AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </motion.div>
        </div>
      </section>

      <section className="pb-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <motion.div
            {...fadeUp}
            className="overflow-hidden rounded-[1.75rem] border border-line bg-gradient-to-br from-white via-accent-soft/40 to-slate-100 px-6 py-12 text-center shadow-lift sm:px-10"
          >
            <h2 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              Ready to generate your next product film?
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-mute">
              Start with a single image or a full reference set. Lumina handles the rest.
            </p>
            <div className="mt-8">
              <PrimaryButton asChild size="lg" variant="accent">
                <Link to="/generate">
                  Open Generator
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </PrimaryButton>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  )
}
