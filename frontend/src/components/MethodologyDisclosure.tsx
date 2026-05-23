export function MethodologyDisclosure({ source, methodology }: { source: string; methodology: string }) {
  if (!source && !methodology) return null;
  return (
    <details className="methodology">
      <summary>Méthodologie &amp; sources</summary>
      {methodology && <p className="methodology__body">{methodology}</p>}
      {source && <p className="methodology__source"><strong>Source :</strong> {source}</p>}
    </details>
  );
}
