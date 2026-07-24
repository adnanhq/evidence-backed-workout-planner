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

/**
 * Resolves an exercise thumbnail, fetching it from the exercises API only when
 * the protocol payload didn't carry one (protocols stashed before the engine
 * started embedding thumbnails). Shares the ["exercise", id] cache entry with
 * the detail page.
 */
export function useExerciseThumbnail(id: string, provided: string | null): string | null {
  const query = useQuery({
    queryKey: ["exercise", id],
    queryFn: () => getExercise(id),
    enabled: Boolean(id) && provided == null,
    staleTime: Infinity,
    retry: 1,
  });
  return provided ?? query.data?.thumbnail ?? null;
}
