import markup from './_current.html?raw';
import './_group.css';
import './refinements.css';

export function Current() {
  return <div className="hero-artwork" onClick={event => {
    if ((event.target as HTMLElement).closest('a')) event.preventDefault();
  }} dangerouslySetInnerHTML={{ __html: markup }} />;
}