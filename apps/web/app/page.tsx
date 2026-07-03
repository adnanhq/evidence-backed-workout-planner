import { Hero } from "@/components/landing/hero";
import { StatBand } from "@/components/landing/stat-band";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Methodology } from "@/components/landing/methodology";
import { SampleProtocol } from "@/components/landing/sample-protocol";
import { Faq } from "@/components/landing/faq";
import { CtaBand } from "@/components/landing/cta-band";

export default function Home() {
  return (
    <>
      <Hero />
      <StatBand />
      <HowItWorks />
      <Methodology />
      <SampleProtocol />
      <Faq />
      <CtaBand />
    </>
  );
}
