import * as vscode from "vscode";

export function underlineStyle(
  prefix: "symbolLinks" | "matchHighlight",
): vscode.DecorationRenderOptions {
  const settings = vscode.workspace.getConfiguration("ctk");
  const style = settings.get<string>(`${prefix}.style`, "solid");
  const color = settings.get<string>(`${prefix}.color`, "");
  return {
    textDecoration: `underline ${["solid", "double", "dotted", "dashed", "wavy"].includes(style) ? style : "solid"}${/^#[\da-f]{6}$/i.test(color) ? ` ${color}` : ""}`,
    rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
  };
}

export function gutterIcon(extensionUri: vscode.Uri): vscode.Uri {
  const color = vscode.workspace
    .getConfiguration("ctk")
    .get<string>("matchHighlight.gutterColor", "");
  return /^#[\da-f]{6}$/i.test(color)
    ? vscode.Uri.parse(
        `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" preserveAspectRatio="none"><path fill="${color}" d="M13 0h3v16h-3z"/></svg>`)}`,
      )
    : vscode.Uri.joinPath(extensionUri, "media", "match-region.svg");
}
