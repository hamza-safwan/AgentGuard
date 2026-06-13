/**
 * Type codegen: read every schemas/v1/*.schema.json and emit a single
 * src/schema.ts containing the equivalent TypeScript types.
 *
 * Invoked by `npm run codegen` and verified in CI via `git diff --exit-code`.
 */

import { compile } from "json-schema-to-typescript";
import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

async function main() {
  const [, , schemaDirArg, outFileArg] = process.argv;
  if (!schemaDirArg || !outFileArg) {
    console.error("usage: tsx scripts/codegen.ts <schema_dir> <out_file>");
    process.exit(2);
  }
  const schemaDir = path.resolve(schemaDirArg);
  const outFile = path.resolve(outFileArg);

  const entries = (await readdir(schemaDir)).filter((n) => n.endsWith(".schema.json"));
  entries.sort();

  const chunks: string[] = [
    "// AUTO-GENERATED FROM schemas/v1/*.schema.json - DO NOT EDIT.",
    "// Run `npm run codegen` to regenerate.",
    "",
  ];

  for (const entry of entries) {
    const raw = await readFile(path.join(schemaDir, entry), "utf-8");
    const schema = JSON.parse(raw);
    const typeName = schema.title ?? toPascal(entry.replace(/\.schema\.json$/, ""));
    schema.title = typeName;
    const ts = await compile(schema, typeName, {
      additionalProperties: false,
      bannerComment: "",
      style: { semi: true, singleQuote: false },
      strictIndexSignatures: true,
    });
    const namespace = `${typeName}Schema`;
    chunks.push(`// ${entry}`);
    chunks.push(`export namespace ${namespace} {`);
    chunks.push(indent(ts.trim()));
    chunks.push("}");
    chunks.push(`export type ${typeName} = ${namespace}.${typeName};`);
    chunks.push("");
  }

  await writeFile(outFile, chunks.join("\n"), "utf-8");
  console.log(`wrote ${outFile} (${entries.length} schemas)`);
}

function indent(src: string): string {
  return src
    .split("\n")
    .map((line) => (line ? `  ${line}` : line))
    .join("\n");
}

function toPascal(name: string): string {
  return name
    .split(/[_\-]/)
    .filter(Boolean)
    .map((p) => p[0]!.toUpperCase() + p.slice(1))
    .join("");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
