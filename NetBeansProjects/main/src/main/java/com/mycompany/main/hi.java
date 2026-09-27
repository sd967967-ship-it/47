import java.util.*;
class test 
{
    public static void main(String args [])
    {
        int a[]={23,43,45,67,54};
        int temp=0;
        for (int i=0;i<5-1;i++)
        for (int j=1;j<5-i-1;i++)
        {
            if (a[j]>a[j+1])
            {
               temp=a[j];
               a[j]=a[j+1];
               a[j+1]=temp;
            }
        }
        for (int i=0;i<5;i++)
        {
           System.out.println(a[i]); 
        }
        int key=43;int flag=0;
        int l=4,b=0,m=0;
        while(l>=b)
        {
            m=(b+l)/2;
            if(a[m]>key)
            l=m-1;
            else if (a[m]<key)
            b=m+1;
            else 
            {
            flag++;
            break;
            }
        }
        if (flag==1)
        System.out.println("match found at position"+(m+1)); 
        else 
        System.out.println("no match found"); 
    }
}