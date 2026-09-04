import React from 'react';

interface LogoProps {
  className?: string;
  size?: number;
}

export const OrganicBrainLogo: React.FC<LogoProps> = ({ className = '', size = 36 }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
    >
      {/* Soft rounded paper-tile container */}
      <rect width="40" height="40" rx="11" fill="#2D3E50" />
      
      {/* Organic brain hemisphere paths & neural synapses */}
      {/* Left hemisphere organic convolutions */}
      <path
        d="M19 10C15 10 11.5 12.5 11 16C10 17 9 19 9 21.5C9 24.5 11 26.5 12.5 27C12 28.5 13 30 15 30.5C17 31 18.5 29.5 19 29V10Z"
        fill="white"
        fillOpacity="0.95"
      />
      <path
        d="M14.5 15.5C13.5 17 14 19 16 19.5"
        stroke="#4F46E5"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      <path
        d="M13 23C14 24.5 16 24 17 25"
        stroke="#4F46E5"
        strokeWidth="1.75"
        strokeLinecap="round"
      />

      {/* Right hemisphere organic convolutions */}
      <path
        d="M21 10C25 10 28.5 12.5 29 16C30 17 31 19 31 21.5C31 24.5 29 26.5 27.5 27C28 28.5 27 30 25 30.5C23 31 21.5 29.5 21 29V10Z"
        fill="white"
        fillOpacity="0.95"
      />
      <path
        d="M25.5 15.5C26.5 17 26 19 24 19.5"
        stroke="#4F46E5"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      <path
        d="M27 23C26 24.5 24 24 23 25"
        stroke="#4F46E5"
        strokeWidth="1.75"
        strokeLinecap="round"
      />

      {/* Central Synaptic Control Node (Institutional Core) */}
      <circle cx="20" cy="19.5" r="2.2" fill="#4F46E5" />
      <circle cx="20" cy="19.5" r="4.2" stroke="#4F46E5" strokeWidth="0.8" strokeOpacity="0.4" />
    </svg>
  );
};
