import { useLayoutEffect, useRef } from 'react';
import { mountHeroVideo } from './_hero-video.js';
import markup from './_cinematic.html?raw';
import './_group.css';
import './refinements.css';
import './hero-video.css';

export function Cinematic() {
  const root = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const hero = root.current?.querySelector<HTMLElement>('[data-hero-videos]');
    if (!hero) return;
    hero.dataset.heroIntro = '';
    hero.dataset.introLang = 'el';
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.documentElement.classList.add('intro-pending');
    }
    return mountHeroVideo(hero);
  }, []);
  return <div ref={root} className="hero-artwork video-hero" onClick={event => {
    if ((event.target as HTMLElement).closest('a')) event.preventDefault();
  }} dangerouslySetInnerHTML={{ __html: markup }} />;
}