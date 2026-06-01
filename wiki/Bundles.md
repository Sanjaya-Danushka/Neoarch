# Bundles

Create and manage package collections with NeoArch Bundles.

## What are Bundles?

Bundles are collections of packages grouped together for easy installation and management. Perfect for:

- **Development Environments** - All tools needed for coding
- **Server Setup** - Complete server configuration
- **System Customization** - Personalized package sets
- **Sharing Configurations** - Easy setup for others

## Creating Bundles

### Step 1: Select Packages

1. Click **Discover** or **Installed** tab
2. Find packages you want to bundle
3. Check the checkbox next to each package

### Step 2: Create Bundle

1. Click **Bundles** tab
2. Click **Create Bundle**
3. Select packages from the list
4. Click **Next**

### Step 3: Configure Bundle

1. **Name** - Give your bundle a descriptive name
2. **Description** - Add details about what's included
3. **Version** - Set bundle version (optional)
4. **Tags** - Add categories (optional)

### Step 4: Save Bundle

1. Review bundle contents
2. Click **Save Bundle**
3. Choose save location
4. Bundle is ready to use!

## Managing Bundles

### View Bundles

**In NeoArch:**
1. Click **Bundles** tab
2. View all created bundles
3. See bundle details

### Edit Bundle

1. Right-click bundle
2. Select **Edit**
3. Modify packages or details
4. Save changes

### Delete Bundle

1. Right-click bundle
2. Select **Delete**
3. Confirm deletion

### Duplicate Bundle

1. Right-click bundle
2. Select **Duplicate**
3. Modify as needed
4. Save new bundle

## Installing from Bundles

### Install Bundle

1. Click **Bundles** tab
2. Select bundle
3. Click **Install Bundle**
4. Authenticate
5. Wait for installation

### Install Specific Packages from Bundle

1. Click **Bundles** tab
2. Select bundle
3. Check specific packages
4. Click **Install Selected**

### Partial Installation

1. Open bundle
2. Uncheck packages you don't want
3. Click **Install**
4. Only selected packages install

## Bundle Examples

### Web Development Bundle

```
- nodejs
- npm
- git
- visual-studio-code
- firefox
- postgresql
- redis
- docker
```

### System Administration Bundle

```
- htop
- iotop
- nethogs
- lsof
- strace
- tmux
- vim
- git
```

### Multimedia Bundle

```
- ffmpeg
- imagemagick
- gimp
- vlc
- audacity
- blender
- krita
```

### Gaming Bundle

```
- steam
- wine
- lutris
- dxvk
- vkd3d
- proton
```

## Sharing Bundles

### Export Bundle

1. Right-click bundle
2. Select **Export**
3. Choose format (JSON, YAML)
4. Save file

### Import Bundle

1. Click **Bundles** tab
2. Click **Import Bundle**
3. Select bundle file
4. Review and confirm
5. Bundle is imported

### Share with Others

**Export and Share:**
1. Export bundle as JSON
2. Share file via email, GitHub, etc.
3. Others can import it

**Example Bundle File:**
```json
{
  "name": "Web Development",
  "version": "1.0",
  "description": "Complete web dev setup",
  "packages": [
    {
      "name": "nodejs",
      "source": "pacman"
    },
    {
      "name": "visual-studio-code",
      "source": "aur"
    }
  ]
}
```

## Advanced Features

### Bundle Dependencies

Bundles can include dependencies:
- Automatically installs required packages
- Resolves version conflicts
- Checks for incompatibilities

### Bundle Profiles

Create multiple profiles:
- **Minimal** - Essential packages only
- **Standard** - Common packages
- **Complete** - All packages

### Scheduled Installation

Schedule bundle installation:
1. Select bundle
2. Click **Schedule Installation**
3. Choose date/time
4. Installation runs automatically

## Use Cases

### Development Environment Setup

**Python Developer Bundle:**
```
- python
- python-pip
- visual-studio-code
- git
- postgresql
- redis
- docker
- postman
```

**Installation:**
1. Import bundle
2. Click **Install Bundle**
3. Wait for completion
4. Ready to develop!

### Server Configuration

**Web Server Bundle:**
```
- nginx
- postgresql
- redis
- certbot
- fail2ban
- htop
- vim
- git
```

### System Optimization

**Performance Bundle:**
```
- preload
- earlyoom
- thermald
- powertop
- iotop
- htop
```

## Best Practices

### Organization

📦 **Name Clearly**
- Use descriptive names
- Include version/date
- Specify purpose

📦 **Document**
- Add descriptions
- List dependencies
- Include setup notes

📦 **Version Control**
- Track bundle versions
- Keep backups
- Document changes

### Maintenance

🔧 **Keep Updated**
- Review packages regularly
- Update dependencies
- Remove obsolete packages

🔧 **Test Before Sharing**
- Install in VM first
- Verify all packages
- Check for conflicts

🔧 **Document Changes**
- Note what changed
- Explain why
- Update version

## Troubleshooting

### Bundle Installation Fails

**Problem:** Installation stops midway

**Solutions:**
- Check internet connection
- Verify disk space
- Check package availability
- Try installing individually

### Package Conflicts

**Problem:** Packages conflict with each other

**Solutions:**
- Remove conflicting package
- Use different source
- Create separate bundle
- Check dependencies

### Missing Packages

**Problem:** Bundle references non-existent packages

**Solutions:**
- Update bundle
- Remove missing packages
- Check package names
- Verify sources

## Tips & Tricks

💡 **Efficiency**
- Create bundles for common tasks
- Share with team members
- Version your bundles
- Keep backups

⚡ **Performance**
- Install bundles during off-hours
- Use wired internet
- Close other applications
- Monitor installation

🔒 **Security**
- Review bundle contents
- Verify package sources
- Check maintainers
- Test in VM first

---

**Need help?** Check [FAQ](FAQ.md) or [Troubleshooting](Troubleshooting.md)
