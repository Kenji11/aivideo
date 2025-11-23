import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Returns the path to the placeholder image
 * @param _width - Image width in pixels (for future use if multiple sizes are added)
 * @param _height - Image height in pixels (for future use if multiple sizes are added)
 * @param _text - Optional text label (for future use)
 * @returns Path to the placeholder image
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function getPlaceholderImage(_width: number = 400, _height: number = 400, _text: string = 'Image'): string {
  return '/placeholder-400x400.jpg';
}
