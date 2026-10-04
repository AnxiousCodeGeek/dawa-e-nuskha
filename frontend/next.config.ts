import type {NextConfig} from 'next';

const backendUrl = (
  process.env.BACKEND_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '');
const nextConfig:NextConfig={
  experimental:{proxyTimeout:190000},
  async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: `${backendUrl}/api/:path*`,
    },
  ];
},
  async headers(){
    return [{source:'/:path*',headers:[
      {key:'X-Content-Type-Options',value:'nosniff'},
      {key:'Referrer-Policy',value:'no-referrer'},
      {key:'Permissions-Policy',value:'camera=(self),microphone=(), geolocation=()'},
      {key:'X-Frame-Options',value:'DENY'},
      {key:'Cache-Control',value:'no-store'}]
            }
           ];
  }
};
export default nextConfig;
