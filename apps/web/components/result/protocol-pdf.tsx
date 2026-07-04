"use client";

import { Document, Page, View, Text, Link, StyleSheet, pdf } from "@react-pdf/renderer";
import { protocolRecapLine, muscleLabel } from "@/lib/labels";
import { tierMeta, tierRank } from "@/lib/evidence";
import type { GenerateResponse, ProtocolSession, ProtocolExercise } from "@/types/protocol";

const styles = StyleSheet.create({
  page: {
    paddingTop: 40,
    paddingBottom: 40,
    paddingHorizontal: 36,
    fontSize: 10,
    fontFamily: "Helvetica",
    color: "#1f2430",
  },
  title: {
    fontSize: 20,
    fontFamily: "Helvetica-Bold",
  },
  recap: {
    marginTop: 4,
    fontSize: 10,
    color: "#6b7280",
  },
  noticeBox: {
    marginTop: 14,
    padding: 10,
    borderWidth: 1,
    borderColor: "#f0dcb8",
    backgroundColor: "#fdf6e8",
    borderRadius: 4,
  },
  noticeTitle: {
    fontSize: 10,
    fontFamily: "Helvetica-Bold",
    color: "#7a5518",
  },
  noticeText: {
    marginTop: 3,
    fontSize: 9,
    color: "#7a5518",
    lineHeight: 1.4,
  },
  session: {
    marginTop: 18,
  },
  sessionHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  sessionBadge: {
    backgroundColor: "#0f766e",
    color: "#ffffff",
    fontSize: 8,
    fontFamily: "Helvetica-Bold",
    paddingVertical: 2,
    paddingHorizontal: 5,
    borderRadius: 3,
  },
  sessionLabel: {
    fontSize: 13,
    fontFamily: "Helvetica-Bold",
  },
  sessionFocus: {
    marginTop: 2,
    fontSize: 9,
    color: "#6b7280",
    fontFamily: "Helvetica-Oblique",
  },
  chipRow: {
    marginTop: 6,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 4,
  },
  chip: {
    fontSize: 8,
    color: "#6b7280",
    borderWidth: 1,
    borderColor: "#d5d9e0",
    borderRadius: 8,
    paddingVertical: 1.5,
    paddingHorizontal: 5,
  },
  exercise: {
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: "#e7e9ee",
  },
  exerciseHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  targetTag: {
    fontSize: 8,
    color: "#6b7280",
    backgroundColor: "#f2f4f7",
    paddingVertical: 1.5,
    paddingHorizontal: 4,
    borderRadius: 3,
  },
  exerciseName: {
    fontSize: 11,
    fontFamily: "Helvetica-Bold",
  },
  rankTag: {
    fontSize: 8,
    color: "#0f766e",
  },
  selectionReason: {
    marginTop: 2,
    fontSize: 9,
    color: "#6b7280",
    fontFamily: "Helvetica-Oblique",
  },
  prescriptionRow: {
    marginTop: 3,
    fontSize: 9.5,
  },
  prescriptionDisplay: {
    fontFamily: "Helvetica-Bold",
  },
  prescriptionRest: {
    color: "#6b7280",
  },
  citationRow: {
    marginTop: 3,
    fontSize: 8,
    color: "#0f766e",
  },
  citationLink: {
    color: "#0f766e",
    textDecoration: "none",
  },
  noCitation: {
    fontSize: 8,
    color: "#6b7280",
  },
  lowerTrustTag: {
    fontSize: 8,
    color: "#7a5518",
  },
  sectionHeading: {
    marginTop: 20,
    fontSize: 14,
    fontFamily: "Helvetica-Bold",
  },
  sectionSubtitle: {
    marginTop: 3,
    fontSize: 9,
    color: "#6b7280",
  },
  evidenceItem: {
    marginTop: 8,
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: "#e7e9ee",
  },
  evidenceMeta: {
    fontSize: 8,
    color: "#6b7280",
  },
  evidenceTitle: {
    marginTop: 2,
    fontSize: 9.5,
    fontFamily: "Helvetica-Bold",
  },
  evidenceSnippet: {
    marginTop: 2,
    fontSize: 8.5,
    color: "#4b5563",
    lineHeight: 1.4,
  },
  footer: {
    position: "absolute",
    bottom: 20,
    left: 0,
    right: 0,
    textAlign: "center",
    fontSize: 8,
    color: "#94a3b8",
  },
});

function ExercisePdfRow({ exercise }: { exercise: ProtocolExercise }) {
  const evidence = exercise.referenceEvidence;
  const hasEvidence = evidence.length > 0;

  return (
    <View style={styles.exercise} wrap={false}>
      <View style={styles.exerciseHeaderRow}>
        <Text style={styles.targetTag}>{exercise.targetLabel}</Text>
        <Text style={styles.exerciseName}>{exercise.name}</Text>
        {exercise.rankDisplay && <Text style={styles.rankTag}>{exercise.rankDisplay}</Text>}
      </View>
      {exercise.selectionReason && (
        <Text style={styles.selectionReason}>{exercise.selectionReason}</Text>
      )}
      {exercise.prescription.display && (
        <Text style={styles.prescriptionRow}>
          <Text style={styles.prescriptionDisplay}>{exercise.prescription.display}</Text>
          {exercise.prescription.rest && (
            <Text style={styles.prescriptionRest}>  ·  {exercise.prescription.rest} rest</Text>
          )}
        </Text>
      )}
      <Text style={styles.citationRow}>
        {hasEvidence ? (
          evidence.map((item, i) => (
            <Text key={(item.pmid ?? "x") + i}>
              {i > 0 ? ", " : ""}
              {tierMeta(item.tier).short}
              {item.pmid ? ` PMID ${item.pmid}` : ""}
              {item.url ? (
                <Link src={item.url} style={styles.citationLink}>
                  {" "}
                  (link)
                </Link>
              ) : null}
            </Text>
          ))
        ) : (
          <Text style={styles.noCitation}>
            No direct study match — selected on catalog ranking
          </Text>
        )}
        {exercise.lowerTrustEvidence && (
          <Text style={styles.lowerTrustTag}>  (Lower-trust)</Text>
        )}
      </Text>
    </View>
  );
}

function SessionPdfBlock({ session }: { session: ProtocolSession }) {
  return (
    <View style={styles.session}>
      <View style={styles.sessionHeaderRow}>
        <Text style={styles.sessionBadge}>Session {session.sessionNumber}</Text>
        <Text style={styles.sessionLabel}>{session.splitLabel}</Text>
      </View>
      {session.focus && <Text style={styles.sessionFocus}>{session.focus}</Text>}
      {session.targetMuscles.length > 0 && (
        <View style={styles.chipRow}>
          {session.targetMuscles.map((m) => (
            <Text key={m} style={styles.chip}>
              {muscleLabel(m)}
            </Text>
          ))}
        </View>
      )}
      {session.exercises.map((exercise, i) => (
        <ExercisePdfRow key={exercise.exerciseId + i} exercise={exercise} />
      ))}
    </View>
  );
}

export function ProtocolPdfDocument({ data }: { data: GenerateResponse }) {
  const sortedEvidence = [...data.evidenceAppendix].sort(
    (a, b) => tierRank(a.tier) - tierRank(b.tier),
  );

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.title}>Your training protocol</Text>
        <Text style={styles.recap}>{protocolRecapLine(data)}</Text>

        {data.usedFallback && (
          <View style={styles.noticeBox}>
            <Text style={styles.noticeTitle}>This plan was generated deterministically</Text>
            <Text style={styles.noticeText}>
              The AI planner was unavailable or its output failed validation, so exercises were
              selected by the evidence-ranked fallback.
            </Text>
          </View>
        )}

        {data.warnings.length > 0 && (
          <View style={styles.noticeBox}>
            <Text style={styles.noticeTitle}>A few honest notes on this plan</Text>
            {data.warnings.map((w, i) => (
              <Text key={i} style={styles.noticeText}>
                •  {w}
              </Text>
            ))}
          </View>
        )}

        {data.sessions.map((session, i) => (
          <SessionPdfBlock key={session.sessionNumber + "-" + i} session={session} />
        ))}

        {sortedEvidence.length > 0 && (
          <View>
            <Text style={styles.sectionHeading}>The evidence behind this protocol</Text>
            <Text style={styles.sectionSubtitle}>
              Every study informing these recommendations — sorted by strength of evidence.
            </Text>
            {sortedEvidence.map((item, i) => (
              <View key={(item.pmid ?? "a") + i} style={styles.evidenceItem} wrap={false}>
                <Text style={styles.evidenceMeta}>
                  {tierMeta(item.tier).label}
                  {item.year ? `  ·  ${item.year}` : ""}
                  {item.pmid ? `  ·  PMID ${item.pmid}` : ""}
                </Text>
                {item.title && <Text style={styles.evidenceTitle}>{item.title}</Text>}
                {item.snippet && <Text style={styles.evidenceSnippet}>{item.snippet}</Text>}
                {item.url && (
                  <Link src={item.url} style={[styles.citationLink, { fontSize: 8 }]}>
                    {item.url}
                  </Link>
                )}
              </View>
            ))}
          </View>
        )}

        <Text
          style={styles.footer}
          fixed
          render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`}
        />
      </Page>
    </Document>
  );
}

export async function downloadProtocolPdf(data: GenerateResponse): Promise<void> {
  const blob = await pdf(<ProtocolPdfDocument data={data} />).toBlob();
  const url = URL.createObjectURL(blob);
  const date = new Date().toISOString().slice(0, 10);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `protocol-${data.request.goal}-${date}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
