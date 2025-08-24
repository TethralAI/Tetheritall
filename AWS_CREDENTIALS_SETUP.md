# AWS Credentials Setup Guide

## For Local Development

### 1. Create AWS Credentials File
Create `~/.aws/credentials` (Windows: `%USERPROFILE%\.aws\credentials`):

```ini
[default]
aws_access_key_id = YOUR_NEW_ACCESS_KEY_HERE
aws_secret_access_key = YOUR_NEW_SECRET_KEY_HERE
region = us-east-1
```

### 2. Create AWS Config File (Optional)
Create `~/.aws/config` (Windows: `%USERPROFILE%\.aws\config`):

```ini
[default]
region = us-east-1
output = json
```

## For CI/CD (GitHub Actions)

### 1. Set GitHub Repository Secrets
Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:
- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_DEFAULT_REGION`: us-east-1

### 2. Use in GitHub Actions Workflow
```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v1
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ${{ secrets.AWS_DEFAULT_REGION }}
```

## Security Best Practices

✅ **DO:**
- Use IAM roles for production deployments
- Rotate credentials regularly
- Use least-privilege IAM policies
- Store credentials in secure locations

❌ **DON'T:**
- Commit credentials to git (git-secrets will prevent this)
- Share credentials in plain text
- Use root account credentials
- Store credentials in code files

## Testing Your Setup

Run this command to verify your credentials work:
```powershell
aws sts get-caller-identity
```

You should see output like:
```json
{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/YourUsername"
}
```
