# NeoArch Website

This folder contains the NeoArch project website that gets deployed to GitHub Pages.

## Setup Instructions

To enable the website:

1. **Go to Repository Settings**:
   - Visit: https://github.com/Sanjaya-Danushka/Aurora/settings

2. **Enable GitHub Pages**:
   - Scroll down to "Pages" section
   - Select "GitHub Actions" as the source
   - The workflow file `.github/workflows/deploy-website.yml` will handle deployment

3. **Alternative Manual Setup** (if needed):
   - In Pages settings, select "Deploy from a branch"
   - Choose `main` branch and `/website` folder
   - This will serve files directly from the `website/` folder

## Website Features

- **Modern responsive design** optimized for desktop and mobile
- **Fast loading** with minimal JavaScript
- **SEO-friendly** with proper meta tags and structure
- **Professional branding** matching NeoArch's identity

## Development

To test locally:
```bash
cd website
python -m http.server 8000
# Visit http://localhost:8000
```

## Deployment

The website automatically deploys when:
- Files in `website/` folder are changed
- The `deploy-website.yml` workflow is triggered
- Website will be available at: `https://sanjaya-danushka.github.io/Neoarch/`

## Customization

- **Colors**: Edit `styles.css` variables in `:root`
- **Content**: Modify `index.html` sections
- **Features**: Add JavaScript in `script.js`

The website is designed to be maintainable and professional, helping establish NeoArch as a serious open-source project.
