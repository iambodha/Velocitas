import { AppProps } from 'next/app';
import '../styles/globals.css'; // Adjust path as needed for your global styles

// Remove the loading indicator by disabling it
import Router from 'next/router';
Router.events.off('routeChangeStart', () => {});
Router.events.off('routeChangeComplete', () => {});
Router.events.off('routeChangeError', () => {});

function MyApp({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}

export default MyApp;