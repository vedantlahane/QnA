import React, { useEffect, useMemo, useRef, useState } from 'react';
import mermaid from 'mermaid';
import type { SqlSchemaPayload, SqlSchemaTable } from '../services/chatApi';

interface SchemaDiagramProps {
  schema: SqlSchemaPayload | null;
}

const sanitizeIdentifier = (value: string, fallback: string): string => {
  const cleaned = value.replace(/[^A-Za-z0-9_]/g, '_');
  return cleaned.length > 0 ? cleaned : fallback;
};

const buildTableDefinition = (table: SqlSchemaTable, alias: string): string[] => {
  const lines: string[] = [`  ${alias} {`];
  table.columns.forEach((column) => {
    const datatype = column.type || 'unknown';
    const descriptor = column.primaryKey ? 'PK' : column.nullable ? 'NULL' : 'NOT NULL';
    lines.push(`    ${datatype} ${column.name} "${descriptor}"`);
  });
  lines.push('  }');
  return lines;
};

const buildMermaidDefinition = (schema: SqlSchemaPayload): string => {
  if (!schema.tables.length) {
    return 'erDiagram\n  EmptySchema {}';
  }

  const lines: string[] = ['erDiagram'];
  const tableAliasMap = new Map<string, string>();

  schema.tables.forEach((table, index) => {
    const alias = sanitizeIdentifier(table.name, `table_${index}`);
    tableAliasMap.set(table.name, alias);
    lines.push(...buildTableDefinition(table, alias));
  });

  schema.tables.forEach((table) => {
    if (!table.foreignKeys?.length) {
      return;
    }
    const targetAlias = tableAliasMap.get(table.name);
    if (!targetAlias) {
      return;
    }
    table.foreignKeys.forEach((fk) => {
      const referencedAlias = tableAliasMap.get(fk.referencedTable);
      if (!referencedAlias) {
        return;
      }
      const label = `${fk.column}->${fk.referencedColumn}`;
      lines.push(`  ${referencedAlias} ||--o{ ${targetAlias} : "${label}"`);
    });
  });

  return lines.join('\n');
};

const SchemaDiagram: React.FC<SchemaDiagramProps> = ({ schema }) => {
  const [svgContent, setSvgContent] = useState<string>('');
  const [renderError, setRenderError] = useState<string | null>(null);
  const renderIdRef = useRef(`schema-${Math.random().toString(36).slice(2)}`);
  const initialisedRef = useRef(false);

  const mermaidDefinition = useMemo(() => {
    if (!schema) {
      return '';
    }
    return buildMermaidDefinition(schema);
  }, [schema]);

  useEffect(() => {
    if (!schema || !mermaidDefinition) {
      setSvgContent('');
      setRenderError(null);
      return;
    }

    if (!initialisedRef.current) {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'loose',
      });
      initialisedRef.current = true;
    }

    mermaid
      .render(`${renderIdRef.current}`, mermaidDefinition)
      .then((output: { svg: string }) => {
        setSvgContent(output.svg);
        setRenderError(null);
      })
      .catch((error: unknown) => {
        setRenderError(error instanceof Error ? error.message : 'Unable to render schema diagram.');
        setSvgContent('');
      });
  }, [mermaidDefinition, schema]);

  if (!schema) {
    return <p className="text-sm text-white/60">No schema information is available.</p>;
  }

  if (renderError) {
    return (
      <div className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-4 text-sm text-rose-200">
        {renderError}
      </div>
    );
  }

  if (!svgContent) {
    return <p className="text-sm text-white/60">Generating schema diagram…</p>;
  }

  return (
    <div
      className="schema-diagram max-h-[420px] overflow-auto rounded-xl border border-white/10 bg-white/5 p-4"
      dangerouslySetInnerHTML={{ __html: svgContent }}
    />
  );
};

export default SchemaDiagram;
