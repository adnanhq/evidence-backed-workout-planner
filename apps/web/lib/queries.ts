import {
  keepPreviousData,
  useMutation,
  useQuery,
} from "@tanstack/react-query";
import {
  generateProtocol,
  getExercise,
  getExercises,
  getTaxonomies,
  type ExerciseQuery,
} from "./api";
import { FALLBACK_TAXONOMIES } from "./taxonomies";

export function useTaxonomies() {
  return useQuery({
    queryKey: ["taxonomies"],
    queryFn: getTaxonomies,
    initialData: FALLBACK_TAXONOMIES,
    staleTime: Infinity,
  });
}

export function useGenerateProtocol() {
  return useMutation({ mutationFn: generateProtocol, retry: false });
}

export function useExercises(params: ExerciseQuery) {
  return useQuery({
    queryKey: ["exercises", params],
    queryFn: () => getExercises(params),
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useExercise(id: string) {
  return useQuery({
    queryKey: ["exercise", id],
    queryFn: () => getExercise(id),
    enabled: Boolean(id),
  });
}
