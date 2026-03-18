import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Shield, BarChart3, FileText, Lock, Users, Zap, ArrowRight, CheckCircle, Brain, TrendingUp, Globe, ChevronRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import heroDashboard from "@/assets/hero-dashboard.jpg";

const features = [
  { icon: Brain, title: "Hybrid AI Scoring", desc: "70% quantitative rules + 30% AI qualitative analysis for the most accurate credit decisions in East Africa.", tag: "AI-Powered" },
  { icon: FileText, title: "Multi-Bureau Reports", desc: "Unified view across TransUnion, Metropol, and Athena with detailed factor breakdowns and trend analysis.", tag: "Reports" },
  { icon: Lock, title: "Credit Freeze & Fraud", desc: "Instant credit freezes, identity theft monitoring, and real-time fraud alerts to protect your clients.", tag: "Security" },
  { icon: TrendingUp, title: "Score Simulator", desc: "What-if analysis lets users see projected score changes before making financial decisions.", tag: "Tools" },
  { icon: Users, title: "Dispute Resolution", desc: "End-to-end dispute management with automated workflows, SLA tracking, and audit trails.", tag: "Compliance" },
  { icon: Globe, title: "Data Sovereignty", desc: "All data processed locally within East Africa. Full compliance with CBK, NBE, and data protection laws.", tag: "Privacy" },
];

const stats = [
  { value: "12,450+", label: "Active Profiles", suffix: "" },
  { value: "98.7", label: "Scoring Accuracy", suffix: "%" },
  { value: "3.2M+", label: "Reports Generated", suffix: "" },
  { value: "<2", label: "Decision Speed", suffix: "s" },
];

const partners = ["NCBA Bank", "Stanbic Bank", "Equity Bank", "KCB Group", "Safaricom", "Co-op Bank"];

const testimonials = [
  { quote: "Athena's hybrid AI model reduced our default rate by 34% in the first quarter. The explainable scoring is exactly what our regulators needed.", name: "Mary Wanjiku", role: "Chief Risk Officer, NCBA Bank", initials: "MW" },
  { quote: "The multi-bureau comparison and real-time alerts have transformed how we assess creditworthiness. Processing time dropped from days to seconds.", name: "James Otieno", role: "Head of Lending, Equity Bank", initials: "JO" },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Nav */}
      <nav className="border-b border-border/50 bg-background/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/25">
              <Shield className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight">Athena</span>
              <span className="text-muted-foreground font-light ml-1">CRB</span>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-foreground transition-colors">How It Works</a>
            <a href="#testimonials" className="hover:text-foreground transition-colors">Testimonials</a>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" className="text-sm" asChild><Link to="/login">Sign In</Link></Button>
            <Button className="text-sm shadow-lg shadow-primary/25" asChild>
              <Link to="/login">Get Started <ArrowRight className="ml-1.5 h-3.5 w-3.5" /></Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative min-h-[90vh] flex items-center">
        {/* Full-cover background image */}
        <div className="absolute inset-0">
          <img src={heroDashboard} alt="" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-background via-background/85 to-background/40" />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-background/30" />
        </div>

        <div className="container mx-auto px-6 py-20 relative">
          <div className="max-w-2xl">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7 }}
            >
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 backdrop-blur-sm px-4 py-1.5 mb-8 text-sm">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                <span className="text-primary font-medium">Powered by Hybrid AI</span>
                <span className="text-muted-foreground">· Licensed by CBK</span>
              </div>

              <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.05] mb-6">
                <span className="bg-clip-text text-transparent" style={{ backgroundImage: "var(--gradient-primary)" }}>
                  Credit Intelligence
                </span>
                <br />
                <span className="text-foreground">for East Africa</span>
              </h1>

              <p className="text-lg text-muted-foreground max-w-lg mb-10 leading-relaxed">
                The first credit bureau powered by explainable AI. Real-time scoring, 
                multi-bureau analysis, and non-collateralized lending decisions — 
                transforming financial data into opportunity.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 mb-12">
                <Button size="lg" className="h-13 px-8 text-base shadow-xl shadow-primary/20 rounded-xl" asChild>
                  <Link to="/login">
                    Access Platform <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" className="h-13 px-8 text-base rounded-xl backdrop-blur-sm" asChild>
                  <Link to="/login">View Live Demo</Link>
                </Button>
              </div>

              {/* Trust badges */}
              <div className="flex items-center gap-6 text-xs text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="h-4 w-4 text-emerald-500" />
                  <span>CBK Licensed</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="h-4 w-4 text-emerald-500" />
                  <span>ISO 27001</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="h-4 w-4 text-emerald-500" />
                  <span>GDPR Compliant</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-border/50 bg-muted/20 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-16">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                className="text-center"
              >
                <div className="text-4xl md:text-5xl font-extrabold tracking-tight mb-2">
                  <span className="bg-clip-text text-transparent" style={{ backgroundImage: "var(--gradient-primary)" }}>
                    {s.value}
                  </span>
                  <span className="text-primary">{s.suffix}</span>
                </div>
                <div className="text-sm text-muted-foreground font-medium">{s.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="relative">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/2 left-0 w-72 h-72 bg-primary/3 rounded-full blur-3xl" />
        </div>
        <div className="container mx-auto px-6 py-24 relative">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-4 py-1.5 mb-6 text-xs text-muted-foreground uppercase tracking-widest font-medium">
              The Athena Hybrid Model
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight mb-4">How Athena Scores Credit</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
              A revolutionary two-part system combining quantitative rules with AI-driven qualitative analysis.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {[
              { step: "01", title: "Data Ingestion", desc: "Transaction history from T24 core banking and mobile money platforms is securely ingested and normalized.", color: "primary" },
              { step: "02", title: "Hybrid Analysis", desc: "Base Score (70%) from quantitative rules + AI Insight (30%) from AI pattern recognition in transaction narratives.", color: "primary" },
              { step: "03", title: "Explainable Decision", desc: "A transparent credit score (300-850) with itemized factor breakdown — every decision is auditable and understandable.", color: "primary" },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.5 }}
                className="relative"
              >
                <div className="text-7xl font-black text-primary/5 absolute -top-4 -left-2">{item.step}</div>
                <div className="relative pt-8">
                  <h3 className="text-lg font-bold mb-2">{item.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
                </div>
                {i < 2 && <ChevronRight className="hidden md:block absolute top-12 -right-5 h-5 w-5 text-muted-foreground/30" />}
              </motion.div>
            ))}
          </div>

          {/* Score formula */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-16 max-w-2xl mx-auto"
          >
            <Card className="border-primary/20 bg-primary/[0.02]">
              <CardContent className="p-6 text-center">
                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-3 font-medium">Scoring Formula</div>
                <div className="text-xl md:text-2xl font-mono font-bold tracking-tight">
                  <span className="text-primary">Final Score</span>
                  <span className="text-muted-foreground mx-2">=</span>
                  <span className="text-foreground">Base Score</span>
                  <span className="text-muted-foreground mx-2">+</span>
                   <span className="text-foreground">AI Insight</span>
                </div>
                <div className="flex items-center justify-center gap-6 mt-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-primary" />70% Quantitative Rules</span>
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" />30% AI Analysis</span>
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500" />±50 pts Bounded</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="bg-muted/20 border-y border-border/50">
        <div className="container mx-auto px-6 py-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight mb-4">Built for Financial Institutions</h2>
            <p className="text-muted-foreground max-w-xl mx-auto text-lg">
              Complete credit bureau infrastructure — from scoring to compliance.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08, duration: 0.5 }}
              >
                <Card className="h-full border-border/50 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 group">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="h-11 w-11 rounded-xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/15 transition-colors">
                        <f.icon className="h-5 w-5 text-primary" />
                      </div>
                      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider bg-muted px-2 py-0.5 rounded-full">{f.tag}</span>
                    </div>
                    <h3 className="font-bold mb-2 text-base">{f.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="container mx-auto px-6 py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight mb-4">Trusted by Leading Banks</h2>
          <p className="text-muted-foreground max-w-xl mx-auto text-lg">
            See how financial institutions across East Africa use Athena.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-16">
          {testimonials.map((t, i) => (
            <motion.div
              key={t.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15 }}
            >
              <Card className="h-full border-border/50">
                <CardContent className="p-6">
                  <p className="text-sm leading-relaxed text-foreground mb-6 italic">"{t.quote}"</p>
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">{t.initials}</div>
                    <div>
                      <div className="text-sm font-semibold">{t.name}</div>
                      <div className="text-xs text-muted-foreground">{t.role}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Partner logos */}
        <div className="text-center">
          <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium mb-6">Trusted by East Africa's leading financial institutions</p>
          <div className="flex flex-wrap items-center justify-center gap-8">
            {partners.map((p) => (
              <span key={p} className="text-sm text-muted-foreground/50 font-semibold tracking-wide">{p}</span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-primary/[0.03]" />
        <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(circle at 1px 1px, hsl(var(--primary) / 0.07) 1px, transparent 0)", backgroundSize: "32px 32px" }} />
        <div className="container mx-auto px-6 py-24 relative text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight mb-4">
              Ready to Transform <br className="hidden md:block" />Credit Decisions?
            </h2>
            <p className="text-lg text-muted-foreground max-w-xl mx-auto mb-10">
              Join the financial institutions using Athena to make smarter, 
              fairer, and faster credit decisions.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" className="h-13 px-10 text-base shadow-xl shadow-primary/20 rounded-xl" asChild>
                <Link to="/login">Start Free Trial <ArrowRight className="ml-2 h-4 w-4" /></Link>
              </Button>
              <Button size="lg" variant="outline" className="h-13 px-10 text-base rounded-xl" asChild>
                <Link to="/login">Schedule Demo</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 bg-muted/10">
        <div className="container mx-auto px-6 py-12">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                  <Shield className="h-4 w-4 text-primary-foreground" />
                </div>
                <span className="font-bold">Athena CRB</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                East Africa's first AI-powered credit bureau. Building a more inclusive 
                financial system through explainable AI and alternative data.
              </p>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-4">Platform</h4>
              <div className="space-y-2 text-xs text-muted-foreground">
                <p>AI Credit Scoring</p>
                <p>Multi-Bureau Reports</p>
                <p>Score Simulator</p>
                <p>Dispute Resolution</p>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-4">Company</h4>
              <div className="space-y-2 text-xs text-muted-foreground">
                <p>About Us</p>
                <p>Careers</p>
                <p>Press</p>
                <p>Contact</p>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-4">Legal</h4>
              <div className="space-y-2 text-xs text-muted-foreground">
                <p>Privacy Policy</p>
                <p>Terms of Service</p>
                <p>Data Protection</p>
                <p>Compliance</p>
              </div>
            </div>
          </div>
          <div className="border-t border-border/50 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-xs text-muted-foreground">© 2025 Athena Credit Bureau. Licensed by Central Bank of Kenya. All rights reserved.</p>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>Nairobi, Kenya</span>
              <span>·</span>
              <span>Addis Ababa, Ethiopia</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
