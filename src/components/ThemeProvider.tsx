'use client';

import { MantineProvider } from '@mantine/core';
import { ReactNode } from 'react';

export default function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <MantineProvider
      defaultColorScheme="auto"
      theme={{
        primaryColor: 'blue',
        colors: {
          dark: [
            '#C1C2C5',
            '#A6A7AB',
            '#909296',
            '#5C5F66',
            '#373A40',
            '#2C2E33',
            '#25262B',
            '#1A1B1E',
            '#141517',
            '#101113',
          ],
        },
      }}
    >
      {children}
    </MantineProvider>
  );
}