"use strict";(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[1139],{50744:function(e,r,n){var t=n(35250),a=n(55344),i=n.n(a);n(70079);var o=function(e){var r=e.children;return(0,t.jsx)(t.Fragment,{children:r})};r.Z=i()(function(){return Promise.resolve(o)},{ssr:!1})},82277:function(e,r,n){n.d(r,{Z:function(){return m}});var t=n(4337),a=n(35250),i=n(70079),o=n(21389),s=n(46020),l=n(33669),u=n(50744),c=n(13090);function d(){var e=(0,t._)(["overflow-hidden w-full h-full relative flex z-0"]);return d=function(){return e},e}function f(){var e=(0,t._)(["relative h-full w-full transition-width overflow-auto"]);return f=function(){return e},e}function m(e){var r=e.children,n=e.showNavigation,t=e.renderTitle,o=e.renderMobileHeaderRightContent,d=e.renderSidebar,f=(0,l.w$)(),g=[],p=null;return i.Children.forEach(r,function(e){i.isValidElement(e)&&(e.type===m.Sidebars?p=e:g.push(e))}),(0,a.jsxs)(v,{children:[f&&n&&(0,a.jsx)(u.Z,{children:(0,a.jsx)(c.l6,{children:d})}),(0,a.jsxs)("div",{className:"relative flex h-full max-w-full flex-1 overflow-hidden",children:[(0,a.jsxs)("div",{className:"flex h-full max-w-full flex-1 flex-col",children:[!f&&n&&(0,a.jsx)(u.Z,{children:(0,a.jsx)(c.Vs,{onClickOpenSidebar:function(){return s.vm.toggleActiveSidebar("mobile-nav")},renderTitle:t,renderSidebar:d,renderRightContent:o})}),(0,a.jsx)(h,{className:"flex-1",children:g})]}),p]})]})}var v=o.Z.div(d()),h=o.Z.main(f());m.Sidebars=function(e){var r=e.children;return(0,a.jsx)(a.Fragment,{children:r})}},13090:function(e,r,n){n.d(r,{H:function(){return M},MP:function(){return w},Vs:function(){return S},js:function(){return C},l6:function(){return R}});var t=n(39324),a=n(70216),i=n(35250),o=n(98359),s=n(20525),l=n(32148),u=n(19841),c=n(97296),d=n(70737),f=n(60554),m=n(70079),v=n(1454),h=n(70671),g=n(32004),p=n(94968),x=n(46020),b=n(33669),k=n(42271),N=n(45635),j=n(20522),y=n(15329);function w(e){var r=e.onClick,n=e.className,o=(0,a._)(e,["onClick","className"]);return(0,i.jsx)(y.zV,(0,t._)({onClick:r,className:(0,u.default)(n,"flex-grow overflow-hidden")},o))}function C(e){var r=e.onClick,n=(0,a._)(e,["onClick"]);return(0,i.jsx)("button",(0,t._)({type:"button",className:"px-3",onClick:r},n))}function M(){var e=(0,h.Z)();return(0,b.w$)()?(0,i.jsx)(N.u,{side:"right",label:e.formatMessage(_.closeSidebar),children:(0,i.jsxs)(y.zV,{onClick:x.vm.toggleDesktopNavCollapsed,className:"w-11 flex-shrink-0 items-center justify-center bg-white dark:bg-transparent",children:[(0,i.jsx)(v.iYc,{className:"icon-sm"}),(0,i.jsx)(l.f,{children:(0,i.jsx)(g.Z,(0,t._)({},_.closeSidebar))})]})}):null}var Z=function(e){var r=e.onClose,n=e.sidebarOpen,a=e.children;return(0,i.jsx)(o.u.Root,{show:n,as:m.Fragment,children:(0,i.jsxs)(s.V,{as:"div",className:"dark relative",onClose:r,children:[(0,i.jsx)(o.u.Child,{as:m.Fragment,enter:"transition-opacity ease-linear duration-300",enterFrom:"opacity-0",enterTo:"opacity-100",leave:"transition-opacity ease-linear duration-300",leaveFrom:"opacity-100",leaveTo:"opacity-0",children:(0,i.jsx)("div",{className:"fixed inset-0 bg-gray-600 bg-opacity-75"})}),(0,i.jsxs)("div",{className:"fixed inset-0 flex",children:[(0,i.jsx)(o.u.Child,{as:m.Fragment,enter:"transition ease-in-out duration-300 transform",enterFrom:"-translate-x-full",enterTo:"translate-x-0",leave:"transition ease-in-out duration-300 transform",leaveFrom:"translate-x-0",leaveTo:"-translate-x-full",children:(0,i.jsxs)(s.V.Panel,{className:"relative flex w-full max-w-xs flex-1 flex-col bg-gray-900",children:[(0,i.jsx)(o.u.Child,{as:m.Fragment,enter:"ease-in-out duration-300",enterFrom:"opacity-0",enterTo:"opacity-100",leave:"ease-in-out duration-300",leaveFrom:"opacity-100",leaveTo:"opacity-0",children:(0,i.jsx)("div",{className:"absolute right-0 top-0 -mr-12 pt-2",children:(0,i.jsxs)("button",{type:"button",className:"ml-1 flex h-10 w-10 items-center justify-center focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white",onClick:r,children:[(0,i.jsx)("span",{className:"sr-only",children:(0,i.jsx)(g.Z,(0,t._)({},_.closeSidebar))}),(0,i.jsx)(v.q5L,{className:"icon-lg text-white","aria-hidden":"true"})]})})}),a]})}),(0,i.jsx)("div",{className:"w-14 flex-shrink-0"})]})]})})},S=function(e){var r=e.onClickOpenSidebar,n=e.renderTitle,a=e.renderSidebar,o=e.renderRightContent,s=(0,x.tN)(function(e){return e.activeSidebar}),l=(0,f.useRouter)().asPath;return(0,m.useEffect)(function(){"mobile-nav"===s&&x.vm.setActiveSidebar(!1)},[l]),(0,i.jsxs)(i.Fragment,{children:[(0,i.jsxs)("div",{className:"sticky top-0 z-10 flex items-center border-b border-white/20 bg-gray-800 pl-1 pt-1 text-gray-200 sm:pl-3 md:hidden",children:[(0,i.jsxs)("button",{type:"button",className:"-ml-0.5 -mt-0.5 inline-flex h-10 w-10 items-center justify-center rounded-md hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white dark:hover:text-white",onClick:r,children:[(0,i.jsx)("span",{className:"sr-only",children:(0,i.jsx)(g.Z,(0,t._)({},_.openSidebar))}),(0,i.jsx)(v.cur,{"aria-hidden":"true",className:"icon-lg"})]}),(0,i.jsx)("h1",{className:"flex-1 text-center text-base font-normal",children:n}),o]}),(0,i.jsx)(Z,{onClose:function(){x.vm.setActiveSidebar(!1)},sidebarOpen:"mobile-nav"===s,children:a})]})};function R(e){var r=e.children,n=(0,h.Z)(),t=(0,m.useRef)(null),a=(0,x.tN)(function(e){return e.isDesktopNavCollapsed}),o=(0,j.Ml)();return(0,i.jsxs)(i.Fragment,{children:[(0,i.jsx)(c.E.div,{className:(0,u.default)("flex-shrink-0 overflow-x-hidden",o?"border-r border-gray-100 bg-gray-50 gizmo:bg-white dark:border-0 dark:bg-gray-900":"dark bg-gray-900"),ref:t,initial:!1,animate:{width:a?0:"260px",transition:{duration:.165,ease:"easeOut"}},onAnimationStart:function(){t.current&&(t.current.style.visibility="visible")},onAnimationComplete:function(){t.current&&a&&(t.current.style.visibility="hidden")},children:(0,i.jsx)("div",{className:"h-full w-[260px]",children:(0,i.jsx)("div",{className:"flex h-full min-h-0 flex-col ",children:r})})}),(0,i.jsx)(d.M,{initial:!1,children:a&&(0,i.jsx)(c.E.div,{className:"absolute left-2 top-2 z-10 hidden md:inline-block",initial:{opacity:0},animate:{opacity:1,transition:{duration:.165,ease:"easeIn"}},children:(0,i.jsx)(N.u,{side:"right",label:n.formatMessage(_.openSidebar),children:(0,i.jsx)(k.O,{onClick:x.vm.toggleDesktopNavCollapsed,"aria-label":n.formatMessage(_.openSidebar),children:(0,i.jsx)(v.iYc,{className:"icon-sm text-black dark:text-white"})})})})})]})}var _=(0,p.vU)({closeSidebar:{id:"navigation.closeSidebar",defaultMessage:"Close sidebar",description:"Close sidebar button label"},openSidebar:{id:"navigation.openSidebar",defaultMessage:"Open sidebar",description:"Open sidebar button label"}})},52696:function(e,r,n){n.d(r,{$3:function(){return m},Ap:function(){return c},CV:function(){return v},GA:function(){return f},Gk:function(){return x},Ix:function(){return g},_O:function(){return p},bE:function(){return b},cI:function(){return h},qH:function(){return d}});var t=n(96237),a=n(70079),i=n(70671),o=n(94968),s=n(62509),l=n(75641),u=n(78931);function c(){var e=(0,i.Z)(),r=e.formatMessage(k.adminRoleName),n=e.formatMessage(k.ownerRoleName),o=e.formatMessage(k.standardRoleName);return(0,a.useMemo)(function(){var e;return e={},(0,t._)(e,l.r3.OWNER,n),(0,t._)(e,l.r3.ADMIN,r),(0,t._)(e,l.r3.STANDARD,o),e},[n,r,o])}function d(e){var r=(0,i.Z)();return e?e.structure===l.CZ.PERSONAL?r.formatMessage(k.personalPlanName):r.formatMessage(k.enterprisePlanName):r.formatMessage(k.personalPlanName)}function f(e){return v((0,i.Z)(),e)}function m(){var e=(0,u.ec)(function(e){return e.currentWorkspace});return v((0,i.Z)(),e)}function v(e,r){var n;return r&&r.structure!==l.CZ.PERSONAL?null!==(n=r.name)&&void 0!==n?n:e.formatMessage(k.defaultWorkspaceTitle):e.formatMessage(k.personalWorkspaceTitle)}function h(){var e,r,n,t,a=(0,s.kP)().session;return null!==(t=null!==(n=null==a?void 0:null===(e=a.user)||void 0===e?void 0:e.name)&&void 0!==n?n:null==a?void 0:null===(r=a.user)||void 0===r?void 0:r.email)&&void 0!==t?t:null}function g(e){var r=(0,u.ec)(function(e){return e.currentWorkspace}),n=(0,u.ec)(u.F_.isPersonalWorkspace),t=(0,u.$T)(),a=f(r),i=h();return e&&!t?e.structure===l.CZ.PERSONAL?i:e.name:r?n?i:a:i}function p(){return(0,u.ec)(function(e){return e.workspaces})}function x(e){var r=p().find(function(r){return r.id===e});return(null==r?void 0:r.role)===l.r3.OWNER}function b(e){var r=p().find(function(r){return r.id===e});return(null==r?void 0:r.role)===l.r3.ADMIN}var k=(0,o.vU)({defaultWorkspaceTitle:{id:"useWorkspaces.defaultWorkspaceTitle",defaultMessage:"Untitled Workspace",description:"title for workspace without a name"},personalWorkspaceTitle:{id:"useWorkspaces.personalWorkspaceTitle",defaultMessage:"Personal account",description:"title for personal workspace"},personalPlanName:{id:"useWorkspaces.personalPlanName",defaultMessage:"Personal",description:"label for personal tier account"},enterprisePlanName:{id:"useWorkspaces.enterprisePlanName",defaultMessage:"Enterprise",description:"label for enterprise tier account"},adminRoleName:{id:"useWorkspaces.adminRoleName",defaultMessage:"Admin",description:"Role name for an admin user"},ownerRoleName:{id:"useWorkspaces.ownerRoleName",defaultMessage:"Owner",description:"Role name for an owner user"},standardRoleName:{id:"useWorkspacews.standardRoleName",defaultMessage:"Member",description:"Role name for a standard user"}})},42271:function(e,r,n){n.d(r,{O:function(){return s},h:function(){return l}});var t=n(4337),a=n(21389);function i(){var e=(0,t._)(["flex p-3 items-center gap-3 transition-colors duration-200 text-gray-600 dark:text-gray-200 cursor-pointer text-sm rounded-md bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 h-11"]);return i=function(){return e},e}function o(){var e=(0,t._)(["h-11 w-11"]);return o=function(){return e},e}var s=a.Z.button(i()),l=a.Z.div(o())},15329:function(e,r,n){n.d(r,{R:function(){return g},Vq:function(){return p},ZB:function(){return v},ZP:function(){return m},zV:function(){return h}});var t=n(4337),a=n(35250),i=n(7813),o=n(19841),s=n(21389);function l(){var e=(0,t._)(["p-2 rounded-md hover:bg-black/10 hover:dark:bg-white/10 cursor-pointer"]);return l=function(){return e},e}function u(){var e=(0,t._)(["flex px-3 min-h-[44px] py-1 items-center gap-3 transition-colors duration-200 dark:text-white cursor-pointer text-sm"]);return u=function(){return e},e}function c(){var e=(0,t._)(["rounded-md border dark:border-white/20 gizmo:min-h-0 hover:bg-gray-500/10 h-11 gizmo:h-10 gizmo:rounded-lg gizmo:border-[rgba(0,0,0,0.1)]"]);return c=function(){return e},e}function d(){var e=(0,t._)(["my-1.5 h-px dark:bg-white/20 bg-black/20"]);return d=function(){return e},e}function f(){var e=(0,t._)(["",""]);return f=function(){return e},e}function m(e){var r=e.onClick,n=e.href,t=e.target,s=e.children;return(0,a.jsx)(i.v.Item,{children:function(e){var i=e.active;return(0,a.jsx)(v,{as:void 0!==n?"a":"button",onClick:r,href:n,target:t,className:(0,o.default)(i?"bg-gray-100 dark:bg-gray-800":"hover:bg-gray-100 dark:hover:bg-gray-800"),children:s})}})}s.Z.a(l());var v=s.Z.a(u()),h=(0,s.Z)(v)(c()),g=s.Z.div(d()),p=(0,s.Z)(v)(f(),function(e){return e.$active?"bg-gray-100 dark:bg-gray-800":"hover:bg-gray-100 dark:hover:bg-gray-800"})}}]);