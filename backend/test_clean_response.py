#!/usr/bin/env python3
"""
Test script to verify the clean_ai_response function works correctly
"""
import re


def clean_ai_response(text: str) -> str:
    """
    Remove code blocks and tool call artifacts from AI response text.
    This prevents UI breaking when the AI response contains code snippets.
    """
    if not text:
        return text
    
    # Remove Python code blocks with ```python ... ```
    text = re.sub(r'```python\s*\n.*?\n```', '', text, flags=re.DOTALL)
    
    # Remove generic code blocks with ``` ... ```
    text = re.sub(r'```\s*\n.*?\n```', '', text, flags=re.DOTALL)
    
    # Remove inline code blocks ` ... `
    text = re.sub(r'`[^`]+`', '', text)
    
    # Remove common tool call patterns like "print(default_api.update_execution_plan(...))"
    text = re.sub(r'print\(default_api\.\w+\([^)]*\)\)', '', text)
    
    # Remove lines that look like tool invocations
    text = re.sub(r'^.*?default_api\.\w+.*?$', '', text, flags=re.MULTILINE)
    
    # Clean up multiple blank lines
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


# Test cases
test_cases = [
    {
        "name": "Python code block with tool call",
        "input": """Here's the execution plan:

## Phase 1: Research
- Research topic X
- Compile notes

Now I will save this plan.
```python
print(default_api.update_execution_plan(project_id="123", plan_content="..."))
```

The plan has been saved.""",
        "expected_contains": ["Phase 1: Research", "Research topic X"],
        "expected_not_contains": ["```python", "print(default_api", "Now I will save"]
    },
    {
        "name": "Multiple code blocks",
        "input": """# Project Plan

Step 1: Do something

```python
code here
```

Step 2: Do another thing

```
more code
```

Step 3: Final step""",
        "expected_contains": ["Project Plan", "Step 1:", "Step 2:", "Step 3:"],
        "expected_not_contains": ["```python", "```", "code here", "more code"]
    },
    {
        "name": "Inline code",
        "input": """Use the `update_plan` function to save changes.""",
        "expected_contains": ["Use the", "function to save changes"],
        "expected_not_contains": ["`update_plan`"]
    },
    {
        "name": "Clean text (no code)",
        "input": """## Execution Plan

### Phase 1
- Task 1
- Task 2

### Phase 2
- Task 3""",
        "expected_contains": ["Execution Plan", "Phase 1", "Phase 2", "Task 1", "Task 2", "Task 3"],
        "expected_not_contains": ["```"]
    }
]


def run_tests():
    """Run all test cases"""
    print("Testing clean_ai_response function...\n")
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        
        result = clean_ai_response(test['input'])
        
        # Check expected content is present
        for expected in test.get('expected_contains', []):
            if expected not in result:
                print(f"  ❌ FAILED: Expected to find '{expected}'")
                print(f"  Result: {result[:200]}...")
                failed += 1
                continue
        
        # Check unwanted content is removed
        all_removed = True
        for unwanted in test.get('expected_not_contains', []):
            if unwanted in result:
                print(f"  ❌ FAILED: Should not contain '{unwanted}'")
                print(f"  Result: {result[:200]}...")
                all_removed = False
                failed += 1
        
        if all_removed and all(expected in result for expected in test.get('expected_contains', [])):
            print(f"  ✅ PASSED")
            passed += 1
        
        print()
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"{'='*50}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
