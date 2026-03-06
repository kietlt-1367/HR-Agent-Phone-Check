# Workflow Configuration Guide

This guide explains how to customize the HR screening interview workflow without writing code.

## Overview

The interview workflow is defined in `workflow_schema.yaml`. You can modify this file to:
- Change interview questions and instructions
- Add or remove tasks
- Modify data fields to collect
- Adjust validation rules
- Customize the flow order

## File Structure

```yaml
workflow:
  name: "Your Workflow Name"
  description: "Description of this workflow"
  timeout_seconds: 1800  # 30 minutes
  language: "vi"  # Language code

tasks:
  - id: "task_id"
    name: "Task Name"
    description: "Brief description"
    instructions: |
      Multi-line instructions for the AI agent...
    on_enter_prompt: "What to say when starting this task"
    tool_name: "function_name"
    tool_description: "What this function does"
    fields:
      - name: "field_name"
        type: "string"
        required: true
        description: "What this field represents"
        validation:
          min_length: 2
          error_message: "Error message if validation fails"
```

## Field Types

Supported field types:
- `string` - Text data (names, descriptions)
- `integer` - Whole numbers (years of experience, salary)
- `float` - Decimal numbers (scores, ratings)
- `boolean` - True/False values (availability)
- `list[string]` - List of text items (questions, skills)

## Validation Rules

You can add validation to ensure data quality:

### String Validation
```yaml
validation:
  min_length: 2
  max_length: 100
  error_message: "Custom error message in Vietnamese"
```

### Integer/Float Validation
```yaml
validation:
  min: 0
  max: 100
  error_message: "Số phải từ 0 đến 100"
```

## Task ID Mapping

**Important:** Task IDs must match these storage keys:
- `personal` → saves to `personal_info`
- `experience` → saves to `work_experience`
- `fit` → saves to `fit_assessment`
- `additional` → saves to `additional_info`
- `closing` → saves to `closing_notes`

If you create new tasks with different IDs, they will be stored as-is.

## Special Task Behaviors

### Closing Task
The last task should have these flags:
```yaml
generate_summary: true  # Generate interview summary
send_webhook: true      # Send results to HR system
```

## Example: Adding a New Task

Want to collect candidate's technical skills? Add this task:

```yaml
  - id: "technical_skills"
    name: "Technical Skills Assessment"
    description: "Đánh giá kỹ năng kỹ thuật"
    instructions: |
      Mục tiêu: Thu thập thông tin về kỹ năng kỹ thuật của ứng viên.
      
      Quy tắc:
      - Hỏi về ngôn ngữ lập trình chính
      - Hỏi về framework/công nghệ đã sử dụng
      - Hỏi về project lớn nhất đã làm
      - Không tóm tắt hoặc đọc lại thông tin
      - Giọng điệu chuyên nghiệp, thân thiện
    
    on_enter_prompt: "Hỏi về kỹ năng kỹ thuật chính của ứng viên."
    
    tool_name: "record_technical_skills"
    tool_description: "Ghi nhận kỹ năng kỹ thuật của ứng viên"
    
    fields:
      - name: "primary_language"
        type: "string"
        required: true
        description: "Ngôn ngữ lập trình chính"
        validation:
          min_length: 2
      
      - name: "frameworks"
        type: "list[string]"
        required: true
        description: "Danh sách framework đã sử dụng"
      
      - name: "years_with_language"
        type: "integer"
        required: true
        description: "Số năm kinh nghiệm với ngôn ngữ chính"
        validation:
          min: 0
          max: 30
```

Then add it to the workflow by placing it in the `tasks` list at the desired position.

## Example: Modifying Existing Fields

Want to collect phone number in personal info? Add this field:

```yaml
  - id: "personal"
    # ... existing config ...
    fields:
      - name: "full_name"
        # ... existing config ...
      
      - name: "applied_position"
        # ... existing config ...
      
      # NEW FIELD:
      - name: "phone_number"
        type: "string"
        required: true
        description: "Số điện thoại liên hệ"
        validation:
          min_length: 10
          max_length: 15
          error_message: "Số điện thoại phải từ 10-15 ký tự"
```

## Example: Changing Instructions

Modify the `instructions` field to change how the AI behaves:

```yaml
  - id: "experience"
    name: "Work Experience"
    instructions: |
      Mục tiêu: Thu thập thông tin chi tiết về kinh nghiệm làm việc.
      
      Quy tắc MỚI:
      - Hỏi về 2-3 công ty gần nhất (thay vì chỉ 1)
      - Hỏi chi tiết về dự án lớn nhất
      - Hỏi về thành tích đáng tự hào
      - Tạo không khí thoải mái, khuyến khích ứng viên kể câu chuyện
```

## Testing Your Changes

After modifying `workflow_schema.yaml`:

1. **Check syntax**: Ensure YAML is valid (proper indentation, no tabs)
2. **Test locally**: Run `uv run pytest tests/test_agent.py`
3. **Deploy**: The agent will automatically load the new workflow on restart

## Common Mistakes

### ❌ Wrong Indentation
```yaml
tasks:
- id: "personal"  # Missing 2 spaces
  fields:
- name: "full_name"  # Wrong level
```

### ✅ Correct Indentation
```yaml
tasks:
  - id: "personal"  # 2 spaces
    fields:
      - name: "full_name"  # 6 spaces
```

### ❌ Using Tabs
YAML does not support tabs. Use spaces only.

### ❌ Missing Required Fields
```yaml
fields:
  - name: "full_name"
    # Missing 'type' - will cause error!
```

### ✅ All Required Fields
```yaml
fields:
  - name: "full_name"
    type: "string"
    required: true
    description: "Họ và tên đầy đủ"
```

## Workflow Execution Order

Tasks execute in the order they appear in the YAML file:

```yaml
tasks:
  - id: "personal"      # Step 1
  - id: "experience"    # Step 2
  - id: "fit"           # Step 3
  - id: "additional"    # Step 4
  - id: "closing"       # Step 5
```

Want to reorder? Just rearrange the list.

## Need Help?

- **YAML Validator**: Use online tools like yamllint.com
- **Field Types**: See "Field Types" section above
- **Examples**: Check existing tasks in `workflow_schema.yaml`
- **Errors**: Check logs in `interview_data/` for debugging

## Advanced: Custom Workflows

You can create completely different workflows for different scenarios:

### Technical Interview
```yaml
workflow:
  name: "Technical Interview"
  description: "In-depth technical assessment"
  
tasks:
  - id: "coding_problem"
  - id: "system_design"
  - id: "behavioral"
  - id: "closing"
```

### Customer Support Screening
```yaml
workflow:
  name: "Customer Support Screening"
  
tasks:
  - id: "communication_skills"
  - id: "customer_scenario"
  - id: "availability"
  - id: "closing"
```

Just save different YAML files and configure the agent to load the appropriate one.
