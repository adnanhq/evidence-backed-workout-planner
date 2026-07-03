import type { Metadata } from "next";
import { ProtocolView } from "@/components/result/protocol-view";

export const metadata: Metadata = {
  title: "Your protocol",
};

export default function ProtocolPage() {
  return <ProtocolView />;
}
