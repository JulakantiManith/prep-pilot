# Implementation Plan: UI/UX Polish

## Overview

This implementation plan covers a comprehensive visual polish pass across the Preply AI frontend. All changes are purely presentational — CSS utility classes, Tailwind config adjustments, and minor component markup styling. No behavioral changes, API calls, routing, or data logic are affected. The approach is incremental: global styles first, then shared components, then feature-specific components, and finally validation.

## Tasks

- [x] 1. Global CSS foundation and utility classes
  - [x] 1.1 Add background glow utility and global animation base rules to `src/index.css`
    - Add `.app-bg-glow` utility class with radial-gradient for dark and light modes
    - Add `.input-focus-glow` utility class for form input focus states
    - Add base-layer rule applying `transition-all duration-200 ease-out` to all interactive elements (button, a, input, select, textarea, [role="button"])
    - Add elevated dark-mode card surface color CSS custom property (--color-card adjustment)
    - _Requirements: 1.1, 1.2, 1.4, 9.1, 9.4, 13.1, 13.2, 13.4_

  - [ ]* 1.2 Write unit tests for global CSS utility class presence
    - Verify `.app-bg-glow` class renders correctly on a container element
    - Verify `.input-focus-glow` class is applied to form inputs
    - _Requirements: 1.1, 9.1_

- [ ] 2. Shared component styling updates
  - [x] 2.1 Update `src/shared/components/Layout.tsx` with background glow and spacing
    - Apply `app-bg-glow` class to the root wrapper div
    - Standardize main content area padding to `p-6`
    - Ensure consistent section gap spacing using `space-y-6`
    - _Requirements: 1.1, 1.2, 2.1, 2.2_

  - [x] 2.2 Update `src/shared/components/Sidebar.tsx` with active state and spacing enhancements
    - Apply blue accent background tint and left border indicator to active nav items
    - Add inset shadow glow on active state (`shadow-[inset_4px_0_8px_-4px] shadow-blue-500/20`)
    - Change nav item spacing from `space-y-1` to `space-y-2` (8px between items)
    - Expand transition from `transition-colors` to `transition-all duration-200`
    - Ensure consistent 12px gap between icon and text with vertical centering
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 2.3 Update `src/shared/components/Navbar.tsx` with alignment consistency
    - Verify and ensure consistent `gap-2` between all action items
    - Verify logo sizing at `h-11 w-11 object-contain` (44px)
    - Ensure header height is `h-16` (64px) with all items vertically centered
    - Ensure branded text renders "Preply" in foreground + "AI" in Blue_Accent
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 2.4 Update `src/shared/components/EmptyState.tsx` with polished styling
    - Add circular gradient background container for icons (`rounded-full bg-gradient-to-br from-muted to-muted/70 shadow-sm`)
    - Ensure spacing: `mt-4` after icon, `mt-2` between title/desc, `mt-6` before action button
    - Ensure title is `text-lg font-semibold`, description is `text-sm text-muted-foreground`
    - Ensure minimum `py-12` vertical padding on the container
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 2.5 Update `src/shared/components/ui/button.tsx` with focus, hover, and disabled styling
    - Change base `transition-colors` to `transition-all duration-200 ease-out`
    - Replace `disabled:pointer-events-none` with `disabled:cursor-not-allowed`
    - Update focus ring: `focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2`
    - Verify size variants: sm=32px, default=40px, lg=48px
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 2.6 Update `src/shared/components/ui/skeleton.tsx` with consistent muted background
    - Ensure skeleton base uses `animate-pulse bg-muted` consistently
    - Verify `rounded-md` for content-shaped placeholders
    - _Requirements: 12.2, 12.4_

  - [ ]* 2.7 Write unit tests for shared component styling
    - Test Button renders with correct transition, focus-visible, and disabled classes
    - Test Sidebar active state applies blue accent indicator classes
    - Test EmptyState renders with correct spacing and typography classes
    - Test Layout applies `app-bg-glow` class
    - _Requirements: 6.1, 8.1, 8.2, 8.3, 11.2, 11.3_

- [x] 3. Checkpoint - Verify shared components
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Feature component styling - Dashboard
  - [x] 4.1 Update `src/features/dashboard/components/MetricsCards.tsx` with premium KPI styling
    - Increase value text to `text-3xl font-extrabold`
    - Add icon container radial glow (`shadow-[0_0_8px_0] shadow-current/20`)
    - Apply standard card hover classes: `hover:shadow-md hover:-translate-y-0.5 hover:border-border`
    - Increase internal padding from `p-4` to `p-6`
    - Apply card base: `rounded-xl border border-border/50 bg-card shadow-sm transition-all duration-200 ease-out`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4_

  - [x] 4.2 Update `src/features/dashboard/components/WeeklyChart.tsx` with chart styling
    - Reduce CartesianGrid stroke opacity to 0.2
    - Ensure tooltip has `borderRadius: "8px"` and shadow styling
    - Verify chart colors use existing `--color-chart-*` variables
    - Wrap chart in card container with `rounded-xl border border-border/50 bg-card shadow-sm`
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 4.3 Update `src/features/dashboard/components/RecentSessions.tsx` with row hover and card styling
    - Add `hover:bg-accent/5` for row highlight on hover
    - Apply `border-border/50` for softer borders
    - Ensure cell padding `px-4 py-3`
    - Apply card container wrapper with standard card classes
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 4.4 Write unit tests for dashboard component styling
    - Test MetricsCards render with `text-3xl font-extrabold` on value elements
    - Test MetricsCards render with icon glow shadow class
    - Test RecentSessions rows have hover background class
    - _Requirements: 4.1, 4.2, 4.3, 10.1_

- [ ] 5. Feature component styling - History
  - [x] 5.1 Update `src/features/history/components/SessionCard.tsx` with table row enhancement
    - Add `hover:bg-accent/5` for subtle row highlight
    - Ensure consistent padding: `px-4 py-3`
    - Apply `border-border/50` for softer border appearance
    - Ensure text sizing: `text-sm` for body, `text-xs` for secondary text
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 5.2 Write unit tests for history component styling
    - Test SessionCard renders with hover highlight class
    - Test SessionCard renders with correct typography classes
    - _Requirements: 10.1, 10.4_

- [x] 6. Form input and auth page styling
  - [x] 6.1 Apply input focus glow to auth pages and profile form inputs
    - Add `input-focus-glow` class to auth page form inputs (login, register, forgot password)
    - Add `input-focus-glow` class to profile page form inputs
    - Ensure consistent `rounded-lg` border radius (8px) on all form inputs
    - Ensure 16px vertical spacing between form field groups
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 6.2 Write unit tests for form input styling
    - Test auth input renders with `input-focus-glow` class
    - Test inputs have consistent border-radius class
    - _Requirements: 9.1, 9.2_

- [x] 7. Branding consistency pass
  - [x] 7.1 Verify and standardize logo rendering across all pages
    - Verify Sidebar mobile header logo uses consistent `h-10 w-10` sizing with branded text
    - Verify Landing page logo uses consistent formatting and `/logo.png` asset
    - Verify Auth pages logo uses consistent formatting and `/logo.png` asset
    - Standardize logo text pattern: "Preply" in foreground + "AI" in `text-blue-600 dark:text-blue-500`
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

- [x] 8. Skeleton loading state improvements
  - [x] 8.1 Replace LoadingSpinner usage with content-shaped skeletons where appropriate
    - Identify dashboard loading states and replace with `MetricsCardsSkeleton` and `ChartSkeleton`
    - Identify history loading states and replace with `ListSkeleton`
    - Ensure all skeleton components use consistent `bg-muted` color and `animate-pulse`
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ]* 8.2 Write unit tests for skeleton loading states
    - Test that skeleton components render with `animate-pulse` class
    - Test that skeleton components render with `bg-muted` class
    - _Requirements: 12.2, 12.4_

- [x] 9. Checkpoint - Final verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- All changes are purely CSS/className modifications — no behavioral or API changes
- No new runtime dependencies are introduced
- The design has no Correctness Properties section, so property-based tests are not applicable
- Testing approach uses Vitest + @testing-library/react for className assertions
- Manual visual testing across light/dark mode and responsive breakpoints is recommended after implementation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "2.5", "2.6"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "6.1", "7.1"] },
    { "id": 3, "tasks": ["2.7", "4.1", "4.2", "4.3", "5.1", "8.1"] },
    { "id": 4, "tasks": ["4.4", "5.2", "6.2", "8.2"] }
  ]
}
```
