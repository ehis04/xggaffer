import { Outlet } from 'react-router-dom';
import ChatPopUp from '../components/predictions/chat/ChatPopUp';

export default function AuthenticatedLayout() {
  return (
    <>
      <Outlet />
      <ChatPopUp />
    </>
  );
}