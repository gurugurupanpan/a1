#!/usr/bin/env python3
"""
Citation Verifier MCP Server

An MCP server that provides tools for verifying academic citations and references.
"""

import json
import re
import sys
from typing import Any

# MCP protocol implementation using stdio
def send_response(response: dict) -> None:
    """Send a JSON-RPC response to stdout."""
    message = json.dumps(response)
    sys.stdout.write(f"Content-Length: {len(message)}\r\n\r\n{message}")
    sys.stdout.flush()


def read_request() -> dict | None:
    """Read a JSON-RPC request from stdin."""
    # Read headers
    headers = {}
    while True:
        line = sys.stdin.readline()
        if line == "\r\n" or line == "\n":
            break
        if not line:
            return None
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    # Read content
    content_length = int(headers.get("Content-Length", 0))
    if content_length > 0:
        content = sys.stdin.read(content_length)
        return json.loads(content)
    return None


def extract_citations(text: str) -> list[dict]:
    """Extract citations from text using common patterns."""
    citations = []

    # Pattern for author-year citations: (Author, Year) or (Author Year)
    author_year_pattern = r'\(([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|&|and)\s+[A-Z][a-zA-Z]+)?)[,\s]+(\d{4}[a-z]?)\)'
    for match in re.finditer(author_year_pattern, text):
        citations.append({
            "type": "author-year",
            "author": match.group(1),
            "year": match.group(2),
            "full_match": match.group(0),
            "position": match.start()
        })

    # Pattern for numbered citations: [1], [2,3], [1-5]
    numbered_pattern = r'\[(\d+(?:[,\-]\d+)*)\]'
    for match in re.finditer(numbered_pattern, text):
        citations.append({
            "type": "numbered",
            "numbers": match.group(1),
            "full_match": match.group(0),
            "position": match.start()
        })

    # Pattern for DOI references
    doi_pattern = r'(?:doi:|https?://doi\.org/)?(10\.\d{4,}/[^\s]+)'
    for match in re.finditer(doi_pattern, text, re.IGNORECASE):
        citations.append({
            "type": "doi",
            "doi": match.group(1),
            "full_match": match.group(0),
            "position": match.start()
        })

    return citations


def verify_citation_format(citation: str) -> dict:
    """Verify if a citation follows standard academic formats."""
    results = {
        "citation": citation,
        "valid": False,
        "format": None,
        "issues": []
    }

    # Check for APA format (Author, Year)
    apa_pattern = r'^[A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|&|and)\s+[A-Z][a-zA-Z]+)?,?\s*\(?\d{4}[a-z]?\)?'
    if re.match(apa_pattern, citation):
        results["valid"] = True
        results["format"] = "APA-like"

    # Check for IEEE format [Number]
    ieee_pattern = r'^\[\d+\]'
    if re.match(ieee_pattern, citation):
        results["valid"] = True
        results["format"] = "IEEE-like"

    # Check for DOI
    doi_pattern = r'^(?:doi:|https?://doi\.org/)?10\.\d{4,}/'
    if re.match(doi_pattern, citation, re.IGNORECASE):
        results["valid"] = True
        results["format"] = "DOI"

    if not results["valid"]:
        results["issues"].append("Citation does not match common academic formats (APA, IEEE, DOI)")

    return results


def check_reference_list(references: list[str]) -> dict:
    """Check a list of references for common issues."""
    results = {
        "total_references": len(references),
        "valid_count": 0,
        "issues": [],
        "details": []
    }

    seen_authors = {}
    years = []

    for i, ref in enumerate(references, 1):
        ref_result = {
            "index": i,
            "reference": ref[:100] + "..." if len(ref) > 100 else ref,
            "issues": []
        }

        # Check for year
        year_match = re.search(r'\b(19|20)\d{2}\b', ref)
        if year_match:
            years.append(int(year_match.group(0)))
        else:
            ref_result["issues"].append("Missing publication year")

        # Check for author names
        author_match = re.match(r'^([A-Z][a-zA-Z]+)', ref)
        if author_match:
            author = author_match.group(1)
            if author in seen_authors:
                seen_authors[author].append(i)
            else:
                seen_authors[author] = [i]
        else:
            ref_result["issues"].append("Does not start with author name")

        # Check for title (should have quoted or italicized text)
        if '"' not in ref and "'" not in ref:
            ref_result["issues"].append("No quoted title found")

        if not ref_result["issues"]:
            results["valid_count"] += 1

        results["details"].append(ref_result)

    # Check for chronological ordering
    if years and years != sorted(years):
        results["issues"].append("References may not be in chronological order")

    # Check for duplicate authors (may need disambiguation)
    for author, indices in seen_authors.items():
        if len(indices) > 1:
            results["issues"].append(f"Multiple references from '{author}' at positions {indices} - ensure proper disambiguation (a, b, c)")

    return results


# MCP Tool definitions
TOOLS = [
    {
        "name": "extract_citations",
        "description": "Extract all citations from a given text. Identifies author-year citations, numbered citations, and DOI references.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to extract citations from"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "verify_citation_format",
        "description": "Verify if a single citation follows standard academic formats (APA, IEEE, DOI).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "citation": {
                    "type": "string",
                    "description": "The citation string to verify"
                }
            },
            "required": ["citation"]
        }
    },
    {
        "name": "check_reference_list",
        "description": "Check a list of references for common issues like missing years, improper ordering, and formatting problems.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "references": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of reference strings to check"
                }
            },
            "required": ["references"]
        }
    }
]


def handle_request(request: dict) -> dict:
    """Handle incoming JSON-RPC requests."""
    method = request.get("method", "")
    request_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "citation-verifier",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "notifications/initialized":
        return None  # No response needed for notifications

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "extract_citations":
                result = extract_citations(arguments.get("text", ""))
            elif tool_name == "verify_citation_format":
                result = verify_citation_format(arguments.get("citation", ""))
            elif tool_name == "check_reference_list":
                result = check_reference_list(arguments.get("references", []))
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def main():
    """Main entry point for the MCP server."""
    while True:
        try:
            request = read_request()
            if request is None:
                break

            response = handle_request(request)
            if response is not None:
                send_response(response)
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            break


if __name__ == "__main__":
    main()
