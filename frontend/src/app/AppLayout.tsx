import { Outlet } from 'react-router';
import styles from './AppLayout.module.css';

export function AppLayout() {
  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#main">
        본문 바로가기
      </a>
      <header className={styles.header}>
        <span className={styles.brand}>YardPilot</span>
      </header>
      <main id="main" className={styles.main} tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
