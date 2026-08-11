var It=Object.defineProperty;var Kt=(o,t,e)=>t in o?It(o,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):o[t]=e;var A=(o,t,e)=>Kt(o,typeof t!="symbol"?t+"":t,e);var U=globalThis,D=U.ShadowRoot&&(U.ShadyCSS===void 0||U.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,G=Symbol(),lt=new WeakMap,j=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==G)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(D&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=lt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&lt.set(e,t))}return t}toString(){return this.cssText}},L=o=>new j(typeof o=="string"?o:o+"",void 0,G),I=(o,...t)=>{let e=o.length===1?o[0]:t.reduce((s,i,n)=>s+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+o[n+1],o[0]);return new j(e,o,G)},ht=(o,t)=>{if(D)o.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=U.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,o.appendChild(s)}},F=D?o=>o:o=>o instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return L(e)})(o):o;var{is:Wt,defineProperty:Bt,getOwnPropertyDescriptor:Gt,getOwnPropertyNames:Ft,getOwnPropertySymbols:qt,getPrototypeOf:Zt}=Object,K=globalThis,ct=K.trustedTypes,Yt=ct?ct.emptyScript:"",Xt=K.reactiveElementPolyfillSupport,M=(o,t)=>o,q={toAttribute(o,t){switch(t){case Boolean:o=o?Yt:null;break;case Object:case Array:o=o==null?o:JSON.stringify(o)}return o},fromAttribute(o,t){let e=o;switch(t){case Boolean:e=o!==null;break;case Number:e=o===null?null:Number(o);break;case Object:case Array:try{e=JSON.parse(o)}catch{e=null}}return e}},pt=(o,t)=>!Wt(o,t),dt={attribute:!0,type:String,converter:q,reflect:!1,useDefault:!1,hasChanged:pt};Symbol.metadata??=Symbol("metadata"),K.litPropertyMetadata??=new WeakMap;var m=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=dt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&Bt(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:n}=Gt(this.prototype,t)??{get(){return this[e]},set(r){this[e]=r}};return{get:i,set(r){let c=i?.call(this);n?.call(this,r),this.requestUpdate(t,c,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??dt}static _$Ei(){if(this.hasOwnProperty(M("elementProperties")))return;let t=Zt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(M("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(M("properties"))){let e=this.properties,s=[...Ft(e),...qt(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(F(i))}else t!==void 0&&e.push(F(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ht(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let n=(s.converter?.toAttribute!==void 0?s.converter:q).toAttribute(e,s.type);this._$Em=t,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let n=s.getPropertyOptions(i),r=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:q;this._$Em=i;let c=r.fromAttribute(e,n.type);this[i]=c??this._$Ej?.get(i)??c,this._$Em=null}}requestUpdate(t,e,s,i=!1,n){if(t!==void 0){let r=this.constructor;if(i===!1&&(n=this[t]),s??=r.getPropertyOptions(t),!((s.hasChanged??pt)(n,e)||s.useDefault&&s.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:n},r){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),n!==!0||r!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,n]of this._$Ep)this[i]=n;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,n]of s){let{wrapped:r}=n,c=this[i];r!==!0||this._$AL.has(i)||c===void 0||this.C(i,void 0,n,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};m.elementStyles=[],m.shadowRootOptions={mode:"open"},m[M("elementProperties")]=new Map,m[M("finalized")]=new Map,Xt?.({ReactiveElement:m}),(K.reactiveElementVersions??=[]).push("2.1.2");var et=globalThis,ut=o=>o,W=et.trustedTypes,_t=W?W.createPolicy("lit-html",{createHTML:o=>o}):void 0,bt="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,At="?"+$,Jt=`<${At}>`,E=document,P=()=>E.createComment(""),z=o=>o===null||typeof o!="object"&&typeof o!="function",st=Array.isArray,Qt=o=>st(o)||typeof o?.[Symbol.iterator]=="function",Z=`[ 	
\f\r]`,N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ft=/-->/g,mt=/>/g,y=RegExp(`>|${Z}(?:([^\\s"'>=/]+)(${Z}*=${Z}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),gt=/'/g,$t=/"/g,yt=/^(?:script|style|textarea|title)$/i,ot=o=>(t,...e)=>({_$litType$:o,strings:t,values:e}),_=ot(1),xe=ot(2),Ee=ot(3),S=Symbol.for("lit-noChange"),h=Symbol.for("lit-nothing"),vt=new WeakMap,x=E.createTreeWalker(E,129);function xt(o,t){if(!st(o)||!o.hasOwnProperty("raw"))throw Error("invalid template strings array");return _t!==void 0?_t.createHTML(t):t}var te=(o,t)=>{let e=o.length-1,s=[],i,n=t===2?"<svg>":t===3?"<math>":"",r=N;for(let c=0;c<e;c++){let a=o[c],d,p,l=-1,u=0;for(;u<a.length&&(r.lastIndex=u,p=r.exec(a),p!==null);)u=r.lastIndex,r===N?p[1]==="!--"?r=ft:p[1]!==void 0?r=mt:p[2]!==void 0?(yt.test(p[2])&&(i=RegExp("</"+p[2],"g")),r=y):p[3]!==void 0&&(r=y):r===y?p[0]===">"?(r=i??N,l=-1):p[1]===void 0?l=-2:(l=r.lastIndex-p[2].length,d=p[1],r=p[3]===void 0?y:p[3]==='"'?$t:gt):r===$t||r===gt?r=y:r===ft||r===mt?r=N:(r=y,i=void 0);let f=r===y&&o[c+1].startsWith("/>")?" ":"";n+=r===N?a+Jt:l>=0?(s.push(d),a.slice(0,l)+bt+a.slice(l)+$+f):a+$+(l===-2?c:f)}return[xt(o,n+(o[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},R=class o{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let n=0,r=0,c=t.length-1,a=this.parts,[d,p]=te(t,e);if(this.el=o.createElement(d,s),x.currentNode=this.el.content,e===2||e===3){let l=this.el.content.firstChild;l.replaceWith(...l.childNodes)}for(;(i=x.nextNode())!==null&&a.length<c;){if(i.nodeType===1){if(i.hasAttributes())for(let l of i.getAttributeNames())if(l.endsWith(bt)){let u=p[r++],f=i.getAttribute(l).split($),w=/([.?@])?(.*)/.exec(u);a.push({type:1,index:n,name:w[2],strings:f,ctor:w[1]==="."?X:w[1]==="?"?J:w[1]==="@"?Q:T}),i.removeAttribute(l)}else l.startsWith($)&&(a.push({type:6,index:n}),i.removeAttribute(l));if(yt.test(i.tagName)){let l=i.textContent.split($),u=l.length-1;if(u>0){i.textContent=W?W.emptyScript:"";for(let f=0;f<u;f++)i.append(l[f],P()),x.nextNode(),a.push({type:2,index:++n});i.append(l[u],P())}}}else if(i.nodeType===8)if(i.data===At)a.push({type:2,index:n});else{let l=-1;for(;(l=i.data.indexOf($,l+1))!==-1;)a.push({type:7,index:n}),l+=$.length-1}n++}}static createElement(t,e){let s=E.createElement("template");return s.innerHTML=t,s}};function C(o,t,e=o,s){if(t===S)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,n=z(t)?void 0:t._$litDirective$;return i?.constructor!==n&&(i?._$AO?.(!1),n===void 0?i=void 0:(i=new n(o),i._$AT(o,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=C(o,i._$AS(o,t.values),i,s)),t}var Y=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??E).importNode(e,!0);x.currentNode=i;let n=x.nextNode(),r=0,c=0,a=s[0];for(;a!==void 0;){if(r===a.index){let d;a.type===2?d=new H(n,n.nextSibling,this,t):a.type===1?d=new a.ctor(n,a.name,a.strings,this,t):a.type===6&&(d=new tt(n,this,t)),this._$AV.push(d),a=s[++c]}r!==a?.index&&(n=x.nextNode(),r++)}return x.currentNode=E,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},H=class o{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=h,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=C(this,t,e),z(t)?t===h||t==null||t===""?(this._$AH!==h&&this._$AR(),this._$AH=h):t!==this._$AH&&t!==S&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Qt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==h&&z(this._$AH)?this._$AA.nextSibling.data=t:this.T(E.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=R.createElement(xt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let n=new Y(i,this),r=n.u(this.options);n.p(e),this.T(r),this._$AH=n}}_$AC(t){let e=vt.get(t.strings);return e===void 0&&vt.set(t.strings,e=new R(t)),e}k(t){st(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let n of t)i===e.length?e.push(s=new o(this.O(P()),this.O(P()),this,this.options)):s=e[i],s._$AI(n),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=ut(t).nextSibling;ut(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,n){this.type=1,this._$AH=h,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=n,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=h}_$AI(t,e=this,s,i){let n=this.strings,r=!1;if(n===void 0)t=C(this,t,e,0),r=!z(t)||t!==this._$AH&&t!==S,r&&(this._$AH=t);else{let c=t,a,d;for(t=n[0],a=0;a<n.length-1;a++)d=C(this,c[s+a],e,a),d===S&&(d=this._$AH[a]),r||=!z(d)||d!==this._$AH[a],d===h?t=h:t!==h&&(t+=(d??"")+n[a+1]),this._$AH[a]=d}r&&!i&&this.j(t)}j(t){t===h?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},X=class extends T{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===h?void 0:t}},J=class extends T{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==h)}},Q=class extends T{constructor(t,e,s,i,n){super(t,e,s,i,n),this.type=5}_$AI(t,e=this){if((t=C(this,t,e,0)??h)===S)return;let s=this._$AH,i=t===h&&s!==h||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,n=t!==h&&(s===h||i);i&&this.element.removeEventListener(this.name,this,s),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},tt=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){C(this,t)}};var ee=et.litHtmlPolyfillSupport;ee?.(R,H),(et.litHtmlVersions??=[]).push("3.3.3");var Et=(o,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let n=e?.renderBefore??null;s._$litPart$=i=new H(t.insertBefore(P(),n),n,void 0,e??{})}return i._$AI(o),i};var it=globalThis,g=class extends m{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Et(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return S}};g._$litElement$=!0,g.finalized=!0,it.litElementHydrateSupport?.({LitElement:g});var se=it.litElementPolyfillSupport;se?.({LitElement:g});(it.litElementVersions??=[]).push("4.2.2");var v="domotiapp-alarm-card",nt="domotiapp-alarm-card-editor",St="DomotiApp Alarm",kt="https://github.com/Sven2410/domotiapp-alarm",k="domotiapp_alarm",b=Object.freeze({get:`${k}/alarms/get`,setEnabled:`${k}/alarms/set_enabled`,skipNext:`${k}/alarms/skip_next`,delete:`${k}/alarms/delete`,stop:`${k}/alarms/stop`,clearMessage:`${k}/alarms/clear_message`,subscribe:`${k}/ringing/subscribe`}),wt="#026FA1";var Ct="person",oe="Kies een persoon in de kaartinstellingen.",Tt="De gekozen persoon bestaat niet meer.",ie="De opgeslagen wekkers van deze persoon zijn onleesbaar.",Ve=Object.freeze(["grid_options","layout_options","view_layout","visibility"]);function Ot(o){if(!o||typeof o!="object"||Array.isArray(o))throw new Error("De kaartconfig ontbreekt of is geen object.");let t=o.person;if(t==null||t==="")return{...o};if(typeof t!="string")throw new Error("'person' moet een entity-ID zijn, zoals person.sven.");if(!t.startsWith(`${Ct}.`))throw new Error(`'${t}' zit niet in het domein ${Ct}. Kies een persoon, zoals person.sven.`);return{...o}}function jt(o){return{type:`custom:${o}`}}function Mt(o,t){return o?t?{soort:"ok",tekst:null,isFout:!1}:{soort:"weg",tekst:Tt,isFout:!0}:{soort:"ontbreekt",tekst:oe,isFout:!1}}function Nt(o,t){return o==="not_found"?Tt:o==="home_assistant_error"?ie:t||"Er ging iets mis bij het ophalen van de wekkers."}var ne="home-assistant";function Pt({leesRegistry:o,definities:t,waarschuw:e=()=>{},plan:s=(a,d)=>setTimeout(a,d),nu:i=()=>Date.now(),marker:n=ne,intervalMs:r=20,maxWachtMs:c=1e4}){let a=i();function d(){let u=o();if(!u)return!1;for(let[f,w]of t)try{u.get(f)||u.define(f,w)}catch(at){e(`kon ${f} niet registreren: ${at&&at.message}`)}return!0}function p(){let u=o();return!u||!u.get(n)?!1:d()}if(p())return!0;let l=()=>{if(!p()){if(i()-a>=c){e(`${n} is na ${c} ms niet verschenen; de kaart wordt alsnog geregistreerd`),d();return}s(l,r)}};return s(l,r),!1}var re=["ma","di","wo","do","vr","za","zo"],zt="Geen wekkers ingesteld",ae="Eenmalig",le="Eenmalig \u2014 afgelopen",he="Morgen overgeslagen",Rt="Geen wekker actief",Ht="Stoppen",ce="Er is een melding over deze wekker, maar de tekst ontbreekt.";function de(o){return!Array.isArray(o)||o.length===0?ae:[...new Set(o)].sort((e,s)=>e-s).map(e=>re[e-1]??"?").join(" ")}function pe(o,t){return!o||Array.isArray(o.days)&&o.days.length>0?!1:Date.parse(o?.one_shot_at??"")<=t}function Vt(o,t){return pe(o,t)?le:o?.skip_next?he:de(o?.days)}function Ut(o){let t=o?.last_message;return!t||typeof t!="object"||Array.isArray(t)?null:{tekst:typeof t.text=="string"&&t.text.trim()?t.text:ce,severity:t.severity==="error"?"error":"notice",isFout:t.severity==="error",kind:typeof t.kind=="string"?t.kind:null}}function Dt(o,t){let e=[...new Set((t??[]).filter(r=>typeof r=="string"))];if(e.length===0)return null;let s=e.map(r=>(o??[]).find(c=>c?.id===r)).filter(Boolean),i=s.map(r=>r.name).filter(Boolean),n=[...new Set(s.map(r=>r.time).filter(Boolean))];return{ids:e,naam:i.length?i.join(" en "):"Wekker",tijd:n.join(" en ")}}var ue="0.1.0",_e="De editor komt in fase 4b. Zet je wekkers voorlopig via de WebSocket-API.",fe="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",me="M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z",Lt="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",ge="M13,14H11V9H13M13,18H11V16H13M1,21H23L12,2L1,21Z",B=(o,t="icoon")=>_`<svg class=${t} viewBox="0 0 24 24" aria-hidden="true">
    <path d=${o} />
  </svg>`,V=class extends g{constructor(){super(),this._toestand=null,this._fout=null,this._menuVoor=null,this._bevestigVoor=null,this._bezig=!1,this._tijdelijkeMelding=null,this._abonnementVoor=null,this._afmelden=null}setConfig(t){let e=Ot(t),s=e.person!==this._config?.person;this._config=e,s&&(this._toestand=null,this._fout=null,this._menuVoor=null,this._bevestigVoor=null,this._herstartAbonnement())}static getConfigElement(){return document.createElement(nt)}static getStubConfig(){return jt(v)}getGridOptions(){return{rows:"auto",columns:12,min_columns:6}}getCardSize(){if(this._stop())return 3;let t=this._toestand?.alarms?.length??0;return 1+Math.max(t,1)}connectedCallback(){super.connectedCallback(),this._herstartAbonnement()}disconnectedCallback(){super.disconnectedCallback(),this._stopAbonnement()}updated(t){t.has("hass")&&this.hass&&this._startAbonnement()}async _startAbonnement(){let t=this._config?.person;if(!(!this.hass||!t||!this.isConnected)&&this._abonnementVoor!==t){this._abonnementVoor=t;try{let e=await this.hass.connection.subscribeMessage(s=>this._opGebeurtenis(s),{type:b.subscribe,person:t});if(this._abonnementVoor!==t){e();return}this._afmelden=e}catch(e){console.warn(`${v}: abonneren mislukt: ${e?.message??e}`)}await this._haalOp()}}_stopAbonnement(){if(this._afmelden){try{this._afmelden()}catch(t){console.warn(`${v}: afmelden mislukt: ${t?.message??t}`)}this._afmelden=null}this._abonnementVoor=null}_herstartAbonnement(){this._stopAbonnement(),this._startAbonnement()}_opGebeurtenis(t){let e=t?.alarm_id,s=t?.event;if(typeof e=="string"&&this._toestand){let i=new Set(this._toestand.ringing??[]);s==="started"?i.add(e):i.delete(e),this._toestand={...this._toestand,ringing:[...i]}}this._haalOp()}async _haalOp(){let t=this._config?.person;if(!(!this.hass||!t))try{let e=await this.hass.callWS({type:b.get,person:t});if(this._config?.person!==t)return;this._toestand=e,this._fout=null}catch(e){if(this._config?.person!==t)return;this._toestand=null,this._fout=Nt(e?.code,e?.message)}}async _roep(t){if(!(!this.hass||this._bezig)){this._bezig=!0;try{let e=await this.hass.callWS(t);e&&typeof e=="object"&&(this._toestand=e,this._fout=null)}catch(e){this._toon(e?.message??"De opdracht is niet gelukt.")}finally{this._bezig=!1}}}_toon(t){this._tijdelijkeMelding=t,clearTimeout(this._meldingTimer),this._meldingTimer=setTimeout(()=>{this._tijdelijkeMelding=null},6e3)}_person(){return this._config?.person}_zetAan(t,e){this._roep({type:b.setEnabled,person:this._person(),alarm_id:t.id,enabled:e})}_overslaan(t){this._menuVoor=null,this._roep({type:b.skipNext,person:this._person(),alarm_id:t.id,skip:!t.skip_next})}_verwijder(t){this._bevestigVoor=null,this._roep({type:b.delete,person:this._person(),alarm_id:t.id})}_begrepen(t){this._roep({type:b.clearMessage,person:this._person(),alarm_id:t.id})}async _stopAlles(t){for(let e of t)await this._roep({type:b.stop,person:this._person(),alarm_id:e})}_stop(){return this._toestand?Dt(this._toestand.alarms,this._toestand.ringing):null}render(){if(!this._config)return h;let t=this._config.person,e=!!(t&&this.hass?.states?.[t]),s=Mt(t,e);if(s.soort!=="ok")return this._mededeling(s.tekst,s.isFout);if(this._fout)return this._mededeling(this._fout,!0);if(!this._toestand)return this._mededeling("Wekkers ophalen\u2026",!1);let i=this._stop();return _`<ha-card>
      ${this._menuVoor?_`<div
            class="sluiter"
            @click=${()=>{this._menuVoor=null}}
          ></div>`:h}
      ${i?this._stopknop(i):this._lijst()}
      ${this._tijdelijkeMelding?_`<div class="onderrij">
            ${B(Lt,"icoon klein")}
            <span class="boodschap">${this._tijdelijkeMelding}</span>
          </div>`:h}
    </ha-card>`}_mededeling(t,e){return _`<ha-card>
      <div class="mededeling ${e?"fout":""}">${t}</div>
    </ha-card>`}_stopknop(t){return _`<button
      class="stopknop"
      @click=${()=>this._stopAlles(t.ids)}
    >
      <div class="stop-tijd">${t.tijd}</div>
      <div class="stop-naam">${t.naam}</div>
      <div class="stop-woord">${Ht}</div>
    </button>`}_lijst(){let t=this._toestand.alarms??[],e=Date.now();return _`
      ${t.length===0?_`<div class="mededeling">${zt}</div>`:t.map(s=>this._rij(s,e))}
      <div class="voet">
        <span class="volgende">
          ${this._toestand.next_fire?.text??Rt}
        </span>
        <button
          class="icoonknop"
          title="Wekker toevoegen"
          aria-label="Wekker toevoegen"
          @click=${()=>this._toon(_e)}
        >
          ${B(fe)}
        </button>
      </div>
    `}_rij(t,e){let s=Ut(t),i=!!t.enabled;return _`
      <div class="rij ${i?"":"uit"}">
        <div class="tijd">${t.time}</div>
        <div class="tekst">
          <div class="naam">${t.name}</div>
          <div class="sub">${Vt(t,e)}</div>
        </div>
        <button
          class="schakelaar"
          role="switch"
          aria-checked=${i?"true":"false"}
          aria-label="Wekker ${t.name} aan of uit"
          @click=${()=>this._zetAan(t,!i)}
        ></button>
        <div class="menuhouder">
          <button
            class="icoonknop"
            title="Meer"
            aria-label="Meer voor ${t.name}"
            @click=${()=>{this._menuVoor=this._menuVoor===t.id?null:t.id}}
          >
            ${B(me)}
          </button>
          ${this._menuVoor===t.id?_`<div class="menu">
                <button @click=${()=>this._overslaan(t)}>
                  ${t.skip_next?"Toch niet overslaan":"Overslaan"}
                </button>
                <button
                  @click=${()=>{this._menuVoor=null,this._bevestigVoor=t.id}}
                >
                  Verwijderen
                </button>
              </div>`:h}
        </div>
      </div>
      ${this._bevestigVoor===t.id?_`<div class="onderrij">
            <span class="boodschap">
              Wekker "${t.name}" van ${t.time} verwijderen?
            </span>
            <button
              class="tekstknop"
              @click=${()=>{this._bevestigVoor=null}}
            >
              Annuleren
            </button>
            <button
              class="tekstknop gevaar"
              @click=${()=>this._verwijder(t)}
            >
              Verwijderen
            </button>
          </div>`:h}
      ${s?_`<div class="onderrij ${s.isFout?"fout":""}">
            ${B(s.isFout?ge:Lt,"icoon klein")}
            <span class="boodschap">${s.tekst}</span>
            <button class="tekstknop" @click=${()=>this._begrepen(t)}>
              Begrepen
            </button>
          </div>`:h}
    `}};A(V,"properties",{hass:{attribute:!1},_config:{state:!0},_toestand:{state:!0},_fout:{state:!0},_menuVoor:{state:!0},_bevestigVoor:{state:!0},_bezig:{state:!0},_tijdelijkeMelding:{state:!0}}),A(V,"styles",I`
    /* unsafeCSS en niet de constante rechtstreeks: lit weigert een gewone
       string in een css-template en gooit dan — op modulescope, wat SPEC 19.4
       verbiedt. De waarde is onze eigen constante en komt nergens van buiten. */
    :host {
      --domotiapp-accent: ${L(wt)};
    }
    /* Geen overflow:hidden op de kaart: dat knipt het overloopmenu van de
       onderste rij af. De stopknop krijgt daarom zelf de hoekafronding van de
       kaart. */
    .sluiter {
      position: fixed;
      inset: 0;
      z-index: 2;
    }
    .mededeling {
      padding: 16px;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-m, 14px);
    }
    .mededeling.fout {
      color: var(--error-color);
    }

    /* --- de lijst --- */
    .rij {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .tijd {
      font-size: 28px;
      line-height: 1.1;
      font-weight: 400;
      color: var(--primary-text-color);
      font-variant-numeric: tabular-nums;
      min-width: 82px;
    }
    .rij.uit .tijd,
    .rij.uit .naam {
      color: var(--secondary-text-color);
    }
    .tekst {
      flex: 1;
      min-width: 0;
    }
    .naam {
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-m, 14px);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .sub {
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }

    /* --- de schakelaar; eigen knop, zie de kop van dit bestand --- */
    .schakelaar {
      flex: 0 0 auto;
      width: 44px;
      height: 24px;
      border-radius: 12px;
      border: none;
      padding: 0;
      cursor: pointer;
      position: relative;
      background: var(--disabled-text-color, #9e9e9e);
      transition: background 0.2s ease;
    }
    .schakelaar[aria-checked="true"] {
      background: var(--domotiapp-accent);
    }
    .schakelaar::after {
      content: "";
      position: absolute;
      top: 2px;
      left: 2px;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--card-background-color, #fff);
      transition: transform 0.2s ease;
    }
    .schakelaar[aria-checked="true"]::after {
      transform: translateX(20px);
    }

    /* --- knoppen en iconen --- */
    button.icoonknop {
      flex: 0 0 auto;
      width: 40px;
      height: 40px;
      border: none;
      border-radius: 50%;
      background: none;
      cursor: pointer;
      color: var(--secondary-text-color);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0;
    }
    button.icoonknop:hover {
      background: var(--divider-color);
    }
    .icoon {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    .icoon.klein {
      width: 18px;
      height: 18px;
      flex: 0 0 auto;
    }

    /* --- overloopmenu --- */
    .menuhouder {
      position: relative;
      flex: 0 0 auto;
    }
    .menu {
      position: absolute;
      right: 0;
      top: 40px;
      z-index: 3;
      min-width: 168px;
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.28);
      overflow: hidden;
    }
    .menu button {
      display: block;
      width: 100%;
      text-align: left;
      padding: 12px 16px;
      border: none;
      background: none;
      cursor: pointer;
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-m, 14px);
      font-family: inherit;
    }
    .menu button:hover {
      background: var(--divider-color);
    }

    /* --- melding en bevestiging op een rij --- */
    .onderrij {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 16px 12px 16px;
      border-bottom: 1px solid var(--divider-color);
      font-size: var(--ha-font-size-s, 12px);
    }
    .onderrij .boodschap {
      flex: 1;
      color: var(--secondary-text-color);
    }
    .onderrij.fout .boodschap,
    .onderrij.fout .icoon {
      color: var(--error-color);
    }
    button.tekstknop {
      border: 1px solid var(--divider-color);
      border-radius: 16px;
      background: none;
      color: var(--primary-text-color);
      padding: 6px 14px;
      cursor: pointer;
      font-size: var(--ha-font-size-s, 12px);
      font-family: inherit;
      white-space: nowrap;
    }
    button.tekstknop:hover {
      background: var(--divider-color);
    }
    button.tekstknop.gevaar {
      color: var(--error-color);
      border-color: var(--error-color);
    }

    /* --- voetregel --- */
    .voet {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-m, 14px);
    }
    .voet .volgende {
      flex: 1;
    }

    /* --- de stoptoestand (SPEC 4) --- */
    button.stopknop {
      display: block;
      width: 100%;
      border: none;
      border-radius: var(--ha-card-border-radius, 12px);
      cursor: pointer;
      background: var(--domotiapp-accent);
      color: #fff;
      padding: 32px 16px;
      font-family: inherit;
      text-align: center;
    }
    .stopknop .stop-tijd {
      font-size: 44px;
      line-height: 1.1;
      font-variant-numeric: tabular-nums;
    }
    .stopknop .stop-naam {
      font-size: var(--ha-font-size-l, 16px);
      opacity: 0.9;
      margin-top: 4px;
    }
    .stopknop .stop-woord {
      margin-top: 20px;
      font-size: 24px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
  `);var O=class O extends g{constructor(){super(...arguments);A(this,"_label",e=>e.name==="person"?"Persoon":e.name)}setConfig(e){this._config={...e}}render(){return!this._config||!this.hass?h:_`
      <div class="uitleg">
        Elke persoon heeft zijn eigen wekkerlijst. De kaart toont alleen de
        wekkers van de gekozen persoon.
      </div>
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${O._SCHEMA}
        .computeLabel=${this._label}
        @value-changed=${this._gewijzigd}
      ></ha-form>
    `}_gewijzigd(e){e.stopPropagation();let s={...this._config,...e.detail.value};this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:s},bubbles:!0,composed:!0}))}};A(O,"properties",{hass:{attribute:!1},_config:{state:!0}}),A(O,"styles",I`
    .uitleg {
      padding: 0 0 12px 0;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }
  `),A(O,"_SCHEMA",[{name:"person",required:!0,selector:{entity:{filter:{domain:"person"}}}}]);var rt=O;Pt({leesRegistry:()=>globalThis.customElements,definities:[[v,V],[nt,rt]],waarschuw:o=>console.warn(`${v}: ${o}`)});window.customCards=window.customCards||[];window.customCards.some(o=>o.type===v)||window.customCards.push({type:v,name:St,description:`Wekkerkaart van DomotiApp (v${ue}).`,preview:!1,documentationURL:kt});
