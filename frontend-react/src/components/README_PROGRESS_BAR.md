# Animated Progress Bar Component

Une barre de progression animée avec effets de shimmer et support multi-variant pour les shorts générés.

## 📦 Composants

### AnimatedProgressBar
Barre de progression linéaire avec animation fluide et effet de scintillement.

#### Props
```typescript
interface AnimatedProgressBarProps {
  progress: number           // 0-100, valeur de progression
  label?: string            // Label à afficher (ex: "Progression")
  showPercentage?: boolean  // Afficher le pourcentage (défaut: true)
  size?: 'sm' | 'md' | 'lg' // Taille de la barre (défaut: 'md')
  variant?: 'default' | 'success' | 'warning' | 'error' // Couleur (défaut: 'default')
  animated?: boolean        // Activer l'animation (défaut: true)
}
```

#### Exemples d'utilisation

**Basique:**
```tsx
<AnimatedProgressBar progress={50} />
```

**Avec label personnalisé:**
```tsx
<AnimatedProgressBar 
  progress={75} 
  label="Téléchargement en cours..."
  size="lg"
/>
```

**Avec variant de succès:**
```tsx
<AnimatedProgressBar 
  progress={100} 
  variant="success"
  label="Téléchargement terminé!"
/>
```

**Sans pourcentage:**
```tsx
<AnimatedProgressBar 
  progress={45}
  showPercentage={false}
  label="Traitement vidéo..."
/>
```

### CircularProgress
Indicateur de progression circulaire avec gradient SVG animé.

#### Props
```typescript
interface CircularProgressProps {
  progress: number                              // 0-100
  size?: 'sm' | 'md' | 'lg'                    // Taille (défaut: 'md')
  variant?: 'default' | 'success' | 'warning' | 'error' // Couleur
  label?: string                                // Label au centre
}
```

#### Exemples d'utilisation

```tsx
<CircularProgress 
  progress={50}
  size="lg"
  variant="default"
  label="Traitement..."
/>
```

## 🎨 Variants Disponibles

| Variant   | Couleurs | Use Case |
|-----------|----------|----------|
| `default` | Purple → Pink | Processus en cours |
| `success` | Green → Emerald | Succès / Complété |
| `warning` | Yellow → Orange | Attention / Avertissement |
| `error`   | Red → Pink | Erreur / Problème |

## 📏 Tailles

| Taille | Hauteur | Usage |
|--------|---------|-------|
| `sm`   | h-2     | Barres compactes |
| `md`   | h-3     | Standard (défaut) |
| `lg`   | h-4     | Barres larges |

## ✨ Fonctionnalités

- ✅ Animation fluide avec transition CSS
- ✅ Effet de shimmer réaliste
- ✅ Support multi-variant (couleurs)
- ✅ Support multi-tailles
- ✅ Pourcentage affichable/masquable
- ✅ Label personnalisable
- ✅ Gestion automatique des valeurs (0-100)
- ✅ Composant CircularProgress bonus

## 🎬 Exemple: Intégration dans GeneratorPage

```tsx
import { AnimatedProgressBar } from '../components/AnimatedProgressBar'

// Dans le composant...
{status && status.status !== 'done' && status.status !== 'error' && (
  <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-8">
    <AnimatedProgressBar
      progress={status.progress}
      label="Progression"
      showPercentage={true}
      size="md"
      variant="default"
      animated={true}
    />
  </div>
)}
```

## 🔧 Personnalisation CSS

Les animations sont définies dans `src/styles/animations.css`:

- `shimmer` - Effet de scintillement
- `pulse-glow` - Effet de lueur pulsante
- `slide-shimmer` - Animation de glissement
- `rainbow-gradient` - Gradient arc-en-ciel (bonus)

## 📝 Tests

Tous les composants ont des tests unitaires avec vitest:

```bash
npm test -- src/components/AnimatedProgressBar.test.tsx
```

## 🚀 Performance

- Utilise CSS transitions pour les animations fluides
- Aucune recalcul de layout pendant l'animation
- Optimisé pour mobile et desktop
- Poids minimal (~2KB minified)

## 🎯 Cas d'usage

1. **Téléchargement de vidéos** - Afficher la progression du téléchargement
2. **Traitement de clips** - Montrer l'avancement du traitement
3. **Upload de fichiers** - Suivi de l'upload
4. **Génération de contenu** - Multi-étapes avec barres progressives
5. **Installation/Mise à jour** - Progression visuelle

## 📦 Intégrations possibles

- `react-query` - Afficher la progression des requêtes
- `socket.io` - Progression en temps réel depuis le serveur
- `Web Workers` - Traitement en arrière-plan avec feedback
