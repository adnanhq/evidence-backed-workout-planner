"use client";

import { useParams } from "next/navigation";
import { ExerciseDetailView } from "@/components/exercises/exercise-detail";

export default function ExerciseDetailPage() {
  const params = useParams<{ id: string }>();
  return <ExerciseDetailView id={params.id} />;
}
